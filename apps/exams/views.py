from django.shortcuts import render
def exam_list(request, group_id): return render(request, "exams/list.html")
def add_exam(request): return render(request, "exams/add.html")
def post_results(request, exam_id): return render(request, "exams/results.html")