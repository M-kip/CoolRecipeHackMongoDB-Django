from django.shortcuts import get_object_or_404, render
from bson import ObjectId
from bson.errors import InvalidId
from django.http import Http404
from django.views.generic.base import TemplateView
from django.views.generic.list import ListView
from django.views.generic import DetailView
from .models import Recipe
# Create your views here.

class index(TemplateView):
    template_name = 'recipes/index.html'

class listRecipes(ListView):
    queryset = Recipe.objects.all().order_by("title")[:20]
    template_name = 'recipes/top_recipes.html'
    #model = Recipe
    context_object_name = 'recipes'

class recipeDetails(DetailView):
    """
    Display a recipe by its MongoDB ObjectId

    Args:
        request: Django request object
        recipe_id: String representation of the MongoDB ObjectId
    """
    model = Recipe
    context_object_name = 'recipe'
    template_name = 'recipes/recipe_details.html'
    pk_url_kwarg = 'recipe_id'

    def dispatch(self, request, *args, **kwargs):
        recipe_id = kwargs['recipe_id']
        # Convert string ID to MongoDB ObjectId
        try:
            object_id = ObjectId(recipe_id)
        except InvalidId:
            raise Http404(f"Invalid recipe ID format: {recipe_id}")
        return super().dispatch(request, *args, **kwargs)

class recipe_statistics(TemplateView):
    template_name = 'recipes/statistics.html'


    def recipe_statistics(self):
        """Define the aggregation pipeline"""
        pipeline = [
            # Stage 1: Extract cuisine from the features subdocument
            {"$project": {"_id": 1, "cuisine": "$features.cuisine"}},
            # Stage 2: Group by cuisine and count occurrences
            {"$group": {"_id": "$cuisine", "count": {"$sum": 1}}},
            # Stage 3: Sort by count in descending order
            {"$sort": {"count": -1}},
            # Stage 4: Reshape the output for better readability
            {
                "$project": {
                    "_id": 1,
                    "cuisine": {"$ifNull": ["$_id", "Unspecified"]},
                    "count": 1,
                }
            },
        ]

        stats = Recipe.objects.raw_aggregate(pipeline)
        return list(stats)
    
    def get_context_data(self, **kwargs):
        # get super context data
        context = super().get_context_data(**kwargs)
        # add in the stats
        context['cuisine_stats'] = self.recipe_statistics()
        return context