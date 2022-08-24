from http import HTTPStatus
import tempfile
import shutil

from django.test import Client, TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache

from posts.forms import PostForm
from posts.models import Post, Group, Comment

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):

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
        cls.uploaded = SimpleUploadedFile(
            name='small_gif.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=cls.uploaded,
        )

        cls.form = PostForm()

        cls.guest = User.objects.create_user(username='guestuser')
        cls.guest_client = Client()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем автора
        self.author_client = Client()
        self.author_client.force_login(PostCreateFormTests.user)

        cache.clear()

    def test_create_post_new_post(self):
        """При отправке валидной формы создается новый пост."""
        posts_count = Post.objects.count()

        form_data = {
            'group': PostCreateFormTests.post.group.id,
            'text': PostCreateFormTests.post.text,
            'image': PostCreateFormTests.uploaded,
        }
        self.author_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                author=PostCreateFormTests.post.author,
                text=PostCreateFormTests.post.text,
                group=PostCreateFormTests.post.group.id,
                image=PostCreateFormTests.post.image,
                id=PostCreateFormTests.post.id,
            ).exclude().exists()
        )

    def test_create_new_post_existing_slug(self):
        """При отправке невалидной формы пост не создается."""
        posts_count = Post.objects.count()
        form_data = {
            'group': PostCreateFormTests.post.group.slug,
            'text': PostCreateFormTests.post.text,
        }
        response = self.author_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_new_post_non_author(self):
        """Не автором пост не создается."""
        posts_count = Post.objects.count()
        new_text = 'Новый пост'
        form_data = {
            'group': self.post.group,
            'text': new_text,
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertRedirects(
            response,
            f'{reverse("login")}?next={reverse("posts:post_create")}'
        )
        self.assertFalse(
            Post.objects.filter(
                group=self.post.group,
                text=new_text,
            ).exists()
        )

    def test_post_edit(self):
        """При отправке валидной формы пост редактируется."""
        posts_count = Post.objects.count()
        r = 'Редакция'
        form_data = {
            'group': self.post.group.id,
            'text': r
        }
        response = self.author_client.post(
            reverse('posts:post_edit', args={PostCreateFormTests.post.id}),
            data=form_data,
            follow=True,
        )

        self.assertTrue(
            Post.objects.filter(
                group=self.post.group.id,
                text=r,
                id=PostCreateFormTests.post.id
            ).exists()
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertFalse(
            Post.objects.filter(
                group=self.post.group,
                text=self.post.text,
            ).exists()
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_comment(self):
        """При отправке валидной формы пост комментируется."""
        comment_count = Comment.objects.filter().count()
        com = 'Комментарий'
        form_data = {'text': com}
        response = self.author_client.post(
            reverse(
                'posts:add_comment',
                args={PostCreateFormTests.post.id}
            ),
            data=form_data,
            follow=True,
        )

        self.assertTrue(
            Comment.objects.filter(
                text=com,
                id=PostCreateFormTests.post.id
            ).exists()
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Comment.objects.count(), comment_count + 1)

    def test_post_non_comment(self):
        """При отправке не авторизованным пользователем комментария пост
         не комментируется."""
        comment_count = Comment.objects.filter().count()
        com = 'Комментарий'
        form_data = {'text': com}
        response = self.guest_client.post(
            reverse(
                'posts:add_comment',
                args={PostCreateFormTests.post.id}
            ),
            data=form_data,
            follow=True,
        )

        self.assertFalse(
            Comment.objects.filter(
                text=com,
                id=PostCreateFormTests.post.id
            ).exists()
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Comment.objects.count(), comment_count)
