from django.urls import path
from .views import index, listRecipes, recipeDetails

app_name = "recipes"
urlpatterns = [
    path("", index.as_view(), name="index"),
    path("top/", listRecipes.as_view(), name="list_recipes"),
    path("recipe/<str:recipe_id>/", recipeDetails.as_view(), name="recipe_detail")
]