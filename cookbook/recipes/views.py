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
from pymongo import MongoClient
from .claude_suggestions_api import get_claude_suggestions

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

class ingredient_vector_search(TemplateView):
    template_name = 'recipes/vector_search.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Try to get from path param first
        search_query = self.kwargs.get('search_query')
        # If not in path, try from query string
        if not search_query:
            search_query = self.request.GET.get('query')
        if search_query:
            ingredient_query = f"Ingredients: {search_query}"
            search_results = perform_vector_search(ingredient_query, limit=10)
            context['query'] = f"Ingredients: {search_query}"
            context["results"] = search_results
            return context
        else:
            return context
    
class ai_meal_suggestions(TemplateView):
        
        """
        View that combines vector search with Claude AI to suggest meals
        based on user-provided ingredients
        """
        template_name = 'recipes/ai_suggestions.html'
        def dispatch(self, request, *args, **kwargs):
            self.query = request.GET.get("ingredients", "")
            self.suggestions = []
            self.error_message = None
            return super().dispatch(request, *args, **kwargs)
        
        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            if self.query:
                try:
                    # Clean up the input - split by commas and strip whitespace
                    ingredients_list = [ing.strip() for ing in self.query.split(",") if ing.strip()]
                    ingredients_text = ", ".join(ingredients_list)

                    # Perform vector search to find similar recipes
                    search_query = f"Ingredients: {ingredients_text}"
                    similar_recipes = perform_vector_search(search_query, limit=10)

                    if similar_recipes:
                        # Format recipe data for Claude
                        recipes_data = []
                        for recipe in similar_recipes:
                            recipes_data.append({
                                "title": recipe.get("title", ""),
                                "ingredients": recipe.get("ingredients", []),
                                "score": recipe.get("similarity_score", 0),
                                "id": recipe.get("id", ""),
                            })

                        # Call Claude API for meal suggestions
                        self.suggestions = get_claude_suggestions(ingredients_list, recipes_data)
                    else:
                        self.error_message = "No similar recipes found for the provided ingredients."

                except Exception as e:
                    self.error_message = f"An error occurred: {str(e)}"

            context.update({
                "ingredients": self.query,
                "suggestions": self.suggestions,
                "error_message": self.error_message,})
            return context

def fuzzy_search(request):
    """
    Simple function-based view for fuzzy search using MongoDB Atlas Search
    """
    query = request.GET.get("q", "")
    recipes = []

    if query:
        # Get MongoDB connection details from environment variables
        MONGO_URI = os.getenv(
            "MONGO_URI", "mongodb://localhost:12404/?directConnection=true"
        )
        MONGO_DB = os.getenv("MONGO_DB", "cookbook")

        # Connect to MongoDB directly for Atlas Search
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db["recipes"]

        # Build the fuzzy search pipeline
        pipeline = [
            {
                "$search": {
                    "index": "default",  # Use the default index
                    "compound": {
                        "should": [
                            {
                                "text": {
                                    "query": query,
                                    "path": "title",
                                    "fuzzy": {"maxEdits": 2, "prefixLength": 2},
                                    "score": {"boost": {"value": 5}},
                                }
                            },
                            {
                                "text": {
                                    "query": query,
                                    "path": "ingredients",
                                    "fuzzy": {"maxEdits": 2, "prefixLength": 1},
                                    "score": {"boost": {"value": 3}},
                                }
                            },
                            {
                                "text": {
                                    "query": query,
                                    "path": "instructions",
                                    "fuzzy": {"maxEdits": 2, "prefixLength": 1},
                                }
                            },
                        ]
                    },
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "title": 1,
                    "ingredients": 1,
                    "instructions": 1,
                    "features": 1,
                    "score": {"$meta": "searchScore"},
                }
            },
            {"$sort": {"score": -1}},
            {"$limit": 50},  # Limit results
        ]

        # Execute the search
        search_results = list(collection.aggregate(pipeline))

        # Extract IDs from search results
        recipe_ids = [result["_id"] for result in search_results]

        # Get Django model instances and preserve ordering
        id_to_position = {str(id): idx for idx, id in enumerate(recipe_ids)}
        recipes_unordered = Recipe.objects.filter(id__in=recipe_ids)

        # Convert to list and sort by search score order
        recipes = list(recipes_unordered)
        recipes.sort(key=lambda r: id_to_position.get(str(r.id), 999))

    # Render the template with results
    return render(request, "recipes/vector_search.html", {"recipes": recipes, "query": query})