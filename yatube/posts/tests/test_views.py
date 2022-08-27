from doctest import master
from http import HTTPStatus
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

from posts.models import Post, Group, Follow
from posts.constants import COUNT_POSTS_PAGE

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.image_post = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post: Post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=cls.image_post,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем авторизованный клиент
        self.user = User.objects.create_user(username='test_author')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        # Создаем автора
        self.author_client = Client()
        self.author_client.force_login(PostPagesTests.user)

        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': self.user}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': PostPagesTests.post.id}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': PostPagesTests.post.id}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_client.get(reverse_name)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def check_page_post(self, context):
        if 'post' in context:
            post = context['post']
        else:
            post = context['page_obj'][0]
        self.assertEqual(post.author, PostPagesTests.post.author)
        self.assertEqual(post.group, PostPagesTests.post.group)
        self.assertEqual(post.text, PostPagesTests.post.text)
        self.assertEqual(post.image, PostPagesTests.post.image)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.check_page_post(response.context)

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug},
                    )
        )
        self.check_page_post(response.context)
        self.assertEqual(response.context['group'], PostPagesTests.group)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:profile',
                                              kwargs={
                                                      'username': 'author'
                                                      }))
        self.check_page_post(response.context)
        self.assertEqual(response.context['author'], PostPagesTests.user)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={
                    'post_id':
                    PostPagesTests.post.id
                }
            )
        )

        self.check_page_post(response.context)

    def test_create_post_page_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.author_client.get(reverse('posts:post_create'))
        reseiving_form = response.context['form']
        self.assertEqual(reseiving_form.instance.text, '')

        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for tp_field, expected in form_fields.items():
            with self.subTest(tp_field=tp_field):
                form_field = response.context.get('form').fields.get(tp_field)
                self.assertIsInstance(form_field, expected)
        self.assertNotIn('is_edit', response.context)

        response = self.author_client.get(reverse('posts:post_edit',
                                          kwargs={
                                                  'post_id':
                                                  PostPagesTests.post.id
                                                  }))

        reseiving_form = response.context['form']
        self.assertEqual(reseiving_form.instance.id, PostPagesTests.post.id)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for tp_field, expected in form_fields.items():
            with self.subTest(tp_field=tp_field):
                form_field = response.context.get('form').fields.get(tp_field)
                self.assertIsInstance(form_field, expected)
        self.assertIs(response.context['is_edit'], True)

    def test_edit_post_absence(self):
        """Редакция поста при смене группы не появляется в старой группе."""

        PostPagesTests.group_2 = Group.objects.create(
            title='Тестовая группа2',
            slug='test-slug2',
        )

        self.author_client.get(
            reverse('posts:group_list',
                    kwargs={'slug': PostPagesTests.group_2.slug}
                    )
        )
        self.assertNotIn(
            PostPagesTests.post.text,
            PostPagesTests.group_2.slug
        )


class FollowViewsTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.follower = User.objects.create_user(username='follower')
        cls.master = User.objects.create_user(username='master')
        cls.not_follower = User.objects.create_user(username='not_follower')

        cls.group = Group.objects.create(
            title='Группа follow',
            slug='slug-follow',
        )
        cls.post = Post.objects.create(
            author=cls.master,
            text='Тест поста follow',
            group=cls.group,
        )

    def setUp(self):
        self.follower_client = Client()
        self.follower_client.force_login(self.follower)
        self.non_follower_client = Client()
        self.non_follower_client.force_login(self.not_follower)

        cache.clear()

    def test_follow(self):
        """Подписка на других пользователей.

        Для авторизованного пользователя
        """
        following = self.follower.following.count()
        response = self.follower_client.post(
            reverse('posts:profile_follow', kwargs={
                'username': self.master.username
            }
            ),
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.master.username})
        )
        self.assertEqual(Follow.objects.count(), following + 1)
        subscript = Follow.objects.first()
        self.assertEqual(subscript.user, self.follower)
        self.assertEqual(subscript.author, self.master)

    def test_unfollow(self):
        """Отписка на других пользователей.

        Для авторизованного пользователя
        """
        Follow.objects.create(user=self.follower, author=self.master)
        response = self.follower_client.post(
            reverse('posts:profile_unfollow', kwargs={
                'username': self.master.username
            }
            ),
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.master.username})
        )
        self.assertEqual(Follow.objects.count(), 0)

    def test_new_post_follower(self):
        """Пост отображается в ленте у подписчиков."""
        Follow.objects.create(user=self.follower, author=self.master)
        response = self.follower_client.post(
            reverse('posts:follow_index'))
        self.assertIn(
            FollowViewsTest.post, response.context['page_obj']
        )

    def test_new_post_not_follower(self):
        """Пост не отображается в ленте у не подписчиков."""
        Follow.objects.create(user=self.follower, author=self.master)
        response = self.non_follower_client.post(
            reverse('posts:follow_index'))
        self.assertNotIn(
            FollowViewsTest.post, response.context['page_obj']
        )


class PaginatorViewsTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug'
        )
        cls.author = User.objects.create_user(username='author')
        cls.posts = []
        for i in range(13):
            cls.posts.append(Post.objects.create(
                text=f'Тестовая запись {i}',
                author=cls.author,
                group=cls.group
            ))

    def setUp(self):
        # Создаем авторизованный клиент
        self.user = User.objects.create_user(username='test_author')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        cache.clear()

    def test_first_page_contains_ten_records(self):
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(
            len(response.context['page_obj']),
            COUNT_POSTS_PAGE
        )

        response = self.authorized_client.get(reverse('posts:group_list',
                                              kwargs={'slug': self.group.slug})
                                              )
        self.assertEqual(
            len(response.context['page_obj'].object_list),
            COUNT_POSTS_PAGE
        )

        response = self.client.get(
            reverse('posts:profile', kwargs={'username': self.author})
        )
        self.assertEqual(
            len(response.context['page_obj'].object_list),
            COUNT_POSTS_PAGE
        )

    def test_second_page_contains_three_records(self):
        response = self.authorized_client.get(
            reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)

        response = self.authorized_client.get(
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}) + '?page=2')
        self.assertEqual(len(response.context['page_obj'].object_list), 3)

        response = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': self.author}) + '?page=2')
        self.assertEqual(len(response.context['page_obj'].object_list), 3)

    def test_cache_index(self):
        """Проверяет работу кэша главной страницы."""
        response = self.authorized_client.get(reverse('posts:index'))
        full_page = response.content
        Post.objects.all().delete()
        response = self.authorized_client.get(reverse('posts:index'))
        cached_page = response.content
        self.assertEqual(
            full_page,
            cached_page
        )
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        cleaned_page = response.content
        self.assertNotEqual(
            full_page,
            cleaned_page
        )
