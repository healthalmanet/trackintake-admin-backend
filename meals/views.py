from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Meal
from .serializers import MealSerializer


# ---------- LIST + CREATE ----------

class MealListCreateAPI(APIView):

    def get(self, request):

        meals = Meal.objects.all()

        serializer = MealSerializer(meals, many=True)

        return Response(serializer.data)


    def post(self, request):

        serializer = MealSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------- UPDATE / DELETE ----------

class MealDetailAPI(APIView):

    def get_object(self, pk):

        try:
            return Meal.objects.get(id=pk)
        except Meal.DoesNotExist:
            return None


    def put(self, request, pk):

        meal = self.get_object(pk)

        if not meal:
            return Response({"error": "Meal not found"}, status=404)

        serializer = MealSerializer(meal, data=request.data)

        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data)

        return Response(serializer.errors, status=400)


    def delete(self, request, pk):

        meal = self.get_object(pk)

        if not meal:
            return Response({"error": "Meal not found"}, status=404)

        meal.delete()

        return Response({"message": "Meal deleted successfully"})