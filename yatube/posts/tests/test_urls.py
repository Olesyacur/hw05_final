from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase, Client
from django.core.cache import cache

from posts.models import Post, Group

User = get_user_model()


class PostUrlTest(TestCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

        cls.guest = User.objects.create_user(username='guestuser')
        cls.guest_client = Client()

    def setUp(self):
        # Создаем неавторизованного клиента, т.е. просто пользователя
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        # Создаем авторизованного пользователя
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        # Создаем автора
        self.author_client = Client()
        self.author_client.force_login(PostUrlTest.user)

        cache.clear()

    def test_urls_exists_at_desired_location(self):
        """Страницы доступны любому пользователю."""
        post_urls = (
            '/',
            f'/group/{PostUrlTest.group.slug}/',
            f'/profile/{PostUrlTest.user}/',
            f'/posts/{PostUrlTest.post.id}/',
        )
        for address in post_urls:
            with self.subTest(address=address):
                response = PostUrlTest.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_not_exists_at_desired_location(self):
        """Страницы не доступны не авторам и не авториз. пользователям."""
        post_urls = (
            f'/posts/{self.post.id}/edit/',
            '/create/',
        )
        for address in post_urls:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.FOUND)

        # Для создания нового поста надо авторизоваться
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(
            response,
            f'{reverse("login")}?next={reverse("posts:post_create")}'
        )
        # Для редактирования поста нужно быть автором
        response = self.guest_client.get(
            f'/posts/{self.post.id}/edit/', follow=True
        )
        self.assertRedirects(
            response,
            f'{reverse("login")}?next='
            f'{reverse("posts:post_edit", kwargs={"post_id": self.post.id})}'
        )
        # Для написания комментария к посту нужно быть автором
        response = self.guest_client.get(
            f'/posts/{self.post.id}/comment/', follow=True
        )
        self.assertRedirects(
            response,
            f'{reverse("login")}?next='
            f'{reverse("posts:add_comment", kwargs={"post_id": self.post.id})}'
        )

    def test_url_not_exists_all_at_desired_location(self):
        """Запрос к несуществующей странице вернет ошибку."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_url_author_exists_at_desired_location(self):
        """Страница доступна только автору."""

        # Создаем не автора, но авторизованного пользователя
        not_author_client = Client()
        not_author_client.force_login(PostUrlTest.guest)

        response = not_author_client.get(
            f'/posts/{PostUrlTest.post.id}/edit/',
            follow=True
        )
        self.assertRedirects(
            response,
            f'/posts/{PostUrlTest.post.id}/',
        )

    def test_url_authorized_exists_at_desired_location(self):
        """Страница доступна только авторизованному пользователю."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_comment_authorized(self):
        """Комментарии доступны только авторизованному пользователю."""
        response = self.authorized_client.get(
            f'/posts/{self.post.id}/comment/',
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_follow_profile_authorized(self):
        """Подписаться доступно только авторизованному пользователю."""
        response = self.authorized_client.get(
            f'/profile/{PostUrlTest.user}/follow/',
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unfollow_profile_authorized(self):
        """Отписаться доступно только авторизованному пользователю."""
        response = self.authorized_client.get(
            f'/profile/{PostUrlTest.user}/unfollow/',
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_public_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{PostUrlTest.group.slug}/': 'posts/group_list.html',
            f'/profile/{PostUrlTest.user}/': 'posts/profile.html',
            f'/posts/{PostUrlTest.post.id}/': 'posts/post_detail.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_private_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            f'/posts/{PostUrlTest.post.id}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.author_client.get(address)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_castom_page_correct_templates(self):
        # Страничка 404
        response = self.guest_client.get('/unexisting_page/')
        self.assertTemplateUsed(
            response,
            'core/404.html'
        )
