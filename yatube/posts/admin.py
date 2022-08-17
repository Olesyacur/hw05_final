from django.contrib import admin

from .models import Post, Group, Comment


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """
    Интерфейс постов на странице сайта.

    Ключевые аргументы:
    list_display - поля из моделей Post и Group
    list_editable - виджет формы группы
    search_fields - поиск по тексту поста
    list_filter - фильтр по дате публикации.
    """

    list_display = (
        'pk',
        'text',
        'pub_date',
        'author',
        'group',
    )
    list_editable = ('group',)
    search_fields = ('text',)
    list_filter = ('pub_date',)
    empty_value_display = '-пусто-'


admin.site.register(Group, prepopulated_fields={"slug": ("title",)})


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """
    Интерфейс комментарий на странице сайта.
    """

    list_display = (
        'pk',
        'post',
        'author',
        'text',
        'created',
    )
    search_fields = ('post',)
    list_filter = ('post',)
    empty_value_display = '-пусто-'
