from django.forms import ModelForm, Textarea
from django import forms
from .models import Post, Comment


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        labels = {'text': 'Текст сообщения', 'group': 'Группа'}
        widgets = {
            'text': Textarea(attrs={'cols': 40, 'rows': 10}),
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)

    def value_text(self):
        text = self.cleaned_data['text']
        if not text:
            raise forms.ValidationError(
                'не заполнено поле комментария'
            )
        return text
