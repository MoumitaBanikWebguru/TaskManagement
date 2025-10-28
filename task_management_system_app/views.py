from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import *
from .models import *

def home_view(request):
    return render(request, 'base.html')

@login_required
def dashboard_view(request):
    """Dashboard for Teacher or Student"""
    user = request.user

    if user_in_group(user, 'Teacher'):
        # Show tasks created by this teacher
        tasks = Task.objects.filter(created_by=user).select_related('assigned_to')
        dashboard_type = 'teacher'
    elif user_in_group(user, 'Student'):
        # Show tasks assigned to this student
        tasks = Task.objects.filter(assigned_to=user).select_related('created_by')
        dashboard_type = 'student'
    else:
        tasks = Task.objects.none()
        dashboard_type = 'none'

    return render(request, 'dashboard.html', {
        'tasks': tasks,
        'dashboard_type': dashboard_type,
    })

def register_view(request):
    """User registration with group selection"""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Registration successful! You can now log in.")
            return redirect('login_view')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


def login_view(request):
    """Custom login using username and password"""
    # if request.user.is_authenticated:
    #     return redirect('task_list')  # redirect if already logged in

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect('task_list')
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


@login_required
def logout_view(request):
    """Logs the user out and redirects to login"""
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login_view')


# ✅ Helper to check group membership
def user_in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


# 📄 LIST VIEW
@login_required
def task_list(request):
    """
    Teachers → see all tasks
    Students → see only their assigned tasks
    """
    if user_in_group(request.user, 'Teacher'):
        tasks = Task.objects.all().order_by('-created_at')
    elif user_in_group(request.user, 'Student'):
        tasks = Task.objects.filter(assigned_to=request.user).order_by('-created_at')
    else:
        tasks = Task.objects.none()

    return render(request, 'tasks.html', {'tasks': tasks})


# ➕ CREATE VIEW (Teacher only)
@login_required
def task_create(request):
    if not user_in_group(request.user, 'Teacher'):
        messages.error(request, "You are not authorized to create tasks.")
        return redirect('task_list')

    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Task created successfully.")
            return redirect('task_list')
    else:
        form = TaskForm()

    return render(request, 'task_form.html', {'form': form, 'title': 'Create Task'})


# ✏️ UPDATE VIEW
@login_required
def task_update(request, pk):
    task = get_object_or_404(Task, pk=pk)

    # 🧠 Teacher → full edit form
    if user_in_group(request.user, 'Teacher'):
        if request.method == 'POST':
            form = TaskForm(request.POST, instance=task)
            if form.is_valid():
                form.save()
                messages.success(request, "Task updated successfully.")
                return redirect('task_list')
        else:
            form = TaskForm(instance=task)
        return render(request, 'task_form.html', {'form': form, 'title': 'Edit Task'})

    # 🧠 Student → can only upload file & change status
    elif user_in_group(request.user, 'Student') and task.assigned_to == request.user:
        if request.method == 'POST':
            task_form = StudentTaskForm(request.POST, instance=task)
            file_form = TaskFileForm(request.POST, request.FILES)

            if task_form.is_valid():
                task_form.save()

            # Handle uploaded files
            files = request.FILES.getlist('file')
            for f in files:
                TaskFile.objects.create(task=task, uploaded_by=request.user, file=f)

            messages.success(request, "Status updated and files uploaded.")
            return redirect('task_list')

        else:
            task_form = StudentTaskForm(instance=task)
            file_form = TaskFileForm()

        uploaded_files = task.files.all()

        return render(
            request,
            'student_task_update.html',
            {
                'task': task,
                'task_form': task_form,
                'file_form': file_form,
                'uploaded_files': uploaded_files,
            }
        )

    else:
        messages.error(request, "You are not authorized to edit this task.")
        return redirect('task_list')


# ❌ DELETE VIEW (Teacher only)
@login_required
def task_delete(request, pk):
    if not user_in_group(request.user, 'Teacher'):
        messages.error(request, "You are not authorized to delete tasks.")
        return redirect('task_list')

    task = get_object_or_404(Task, pk=pk)
    task.delete()
    messages.success(request, "Task deleted successfully.")
    return redirect('task_list')