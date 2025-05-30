from unittest import result
import voyageai
import os
from anthropic import Anthropic
from django.shortcuts import get_object_or_404, render
from bson import ObjectId
from bson.errors import InvalidId
from django.http import Http404
from django.views.generic.base import TemplateView
from django.views.generic.list import ListView
from django.views.generic import DetailView
from .models import Recipe
from dotenv import load_dotenv

load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
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

def perform_vector_search(query_text, limit=10, num_candidates=None):
    if num_candidates is None:
        num_candidates = limit * 3

    try:
        # Generate embedding for the search query
        vo = voyageai.Client()  # Uses VOYAGE_API_KEY from environment
        query_embedding = vo.embed(
            [query_text], model="voyage-lite-01-instruct", input_type="query"
        ).embeddings[0]

        # Use Django's raw_aggregate to perform vector search
        results = Recipe.objects.raw_aggregate(
            [
                {
                    "$vectorSearch": {
                        "index": "recipe_vector_index",
                        "path": "voyage_embedding",
                        "queryVector": query_embedding,
                        "numCandidates": num_candidates,
                        "limit": limit,
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "title": 1,
                        "ingredients": 1,
                        "instructions": 1,
                        "features": 1,
                        "score": {"$meta": "vectorSearchScore"},
                    }
                },
            ]
        )

        # Format the results - accessing attributes directly
        recipes = []
        for recipe in results:
            try:
                # Try direct attribute access first
                recipe_dict = {
                    "id": str(recipe.id),
                    "title": recipe.title,
                    "ingredients": recipe.ingredients,
                    "instructions": getattr(recipe, "instructions", ""),
                    "features": getattr(recipe, "features", {}),
                    "similarity_score": getattr(recipe, "score", 0),
                }
                recipes.append(recipe_dict)
            except Exception as e:
                print(f"Error formatting recipe: {str(e)}")
        return recipes

    except Exception as e:
        print(f"Error in vector search: {str(e)}")
        return []

class ingredient_vector_search(DetailView):
    template_name = 'recipes/vector_search.html'
    pk_url_kwarg = 'search_query'
    context_object_name = "results"

    def get_object(self, queryset = ...):
        ingredient_query = f"Ingredients: {self.pk_url_kwarg}"
        queryset = perform_vector_search(ingredient_query, limit=10)
        self.object = queryset
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = f"Ingredients: {kwargs.get(self.pk_url_kwarg)}"
        return context
