from django.contrib import admin

from .models import Post, Group


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


admin.site.register(Group)
