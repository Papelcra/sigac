from django import forms
from cinema.models import Show, Movie, Room

class MovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        fields = ['title', 'description', 'duration', 'release_date', 'poster', 'active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'release_date': forms.DateInput(attrs={'type': 'date'}),
            'poster': forms.FileInput(attrs={'accept': 'image/*'}),
        }

class ShowForm(forms.ModelForm):
    class Meta:
        model = Show
        fields = ['movie', 'room', 'date', 'time', 'base_price', 'active']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
            'movie': forms.Select(attrs={'class': 'form-select'}),
            'room': forms.Select(attrs={'class': 'form-select'}),
        }