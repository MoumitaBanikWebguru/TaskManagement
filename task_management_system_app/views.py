from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .forms import *
from .models import *
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password


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
    """User registration with group selection + HTML email verification"""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            # Add group manually (commit=False skips form.save() group logic)
            group = form.cleaned_data['group']
            user.groups.add(group)

            # Create verification token (2-hour expiry)
            token_obj = EmailVerification.objects.create(
                user=user,
                expires_at=timezone.now() + timedelta(minutes=5)
            )

            # Build verification link safely
            verify_link = request.build_absolute_uri(
                reverse('verify_email', args=[str(token_obj.token)])
            )

            # Render HTML email template
            context = {
                'user': user,
                'verify_link': verify_link,
                'current_year': timezone.now().year,
            }
            html_content = render_to_string('emails/verify_email.html', context)
            text_content = strip_tags(html_content)

            subject = "Verify your email - Task Management"
            email = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )
            email.attach_alternative(html_content, "text/html")

            try:
                email.send()
                messages.success(request, "Registration successful! Please check your email to verify your account.")
            except Exception as e:
                messages.error(request, "Could not send verification email. Please try again later.")
                print("Email error:", e)

            return redirect('login_view')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})

def verify_email(request, token):
    token_obj = get_object_or_404(EmailVerification, token=token)

    # 1️⃣ Check expiry
    if token_obj.is_expired():
        messages.error(request, "Verification link has expired. Please register again.")
        token_obj.delete()
        return redirect('register_view')

    # 2️⃣ Activate user
    user = token_obj.user
    user.is_active = True
    user.save()

    # 3️⃣ Mark token as verified
    token_obj.is_verified = True
    token_obj.save()

    # 4️⃣ Send welcome email using send_mail()
    try:
        subject = "Welcome to Task Management!"
        message = (
            f"Hi {user.username},\n\n"
            "🎉 Your email has been successfully verified!\n\n"
            "Welcome to Task Management — you can now log in and start organizing your work.\n\n"
            "Login here: http://127.0.0.1:8000/login/\n\n"
            "Best regards,\n"
            "The Task Management Team"
        )
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]

        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        print(f"✅ Welcome email sent to {user.email}")

    except Exception as e:
        print("⚠️ Error sending welcome email:", e)

    # 5️⃣ Show success message & redirect
    messages.success(request, "Email verified successfully! You can now log in.")
    return redirect('login_view')

def login_view(request):
    """Custom login using username and password with email verification check"""

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)

            if user is not None:
                try:
                    verification = EmailVerification.objects.get(user=user)
                except EmailVerification.DoesNotExist:
                    verification = None

                # 1️⃣ Check if email verified
                if verification and verification.is_verified:
                    # 2️⃣ Check if user active
                    if user.is_active:
                        login(request, user)
                        messages.success(request, f"Welcome back, {user.username}!")
                        return redirect('task_list')
                    else:
                        messages.error(request, "Your account is inactive. Contact admin.")
                else:
                    messages.error(request, "Please verify your email before logging in.")
                    return redirect('login_view')

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


# 1️⃣ Forgot Password View
def forgot_password_view(request):
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.filter(email=email).first()

            if user:
                token = PasswordResetToken.objects.create(user=user)
                reset_link = request.build_absolute_uri(
                    reverse('reset_password', args=[str(token.token)])
                )

                # Render HTML email
                context = {'user': user, 'reset_link': reset_link}
                html_content = render_to_string('emails/reset_password.html', context)
                text_content = strip_tags(html_content)

                subject = "Reset your password - Task Management"
                email_msg = EmailMultiAlternatives(
                    subject, text_content, settings.DEFAULT_FROM_EMAIL, [email]
                )
                email_msg.attach_alternative(html_content, "text/html")
                email_msg.send()

                messages.success(request, "Password reset link has been sent to your email.")
                return redirect('login_view')
            else:
                messages.error(request, "No user found with this email.")
    else:
        form = ForgotPasswordForm()

    return render(request, 'forgot_password.html', {'form': form})


# 2️⃣ Reset Password View
def reset_password_view(request, token):
    try:
        reset_token = PasswordResetToken.objects.get(token=token)
    except PasswordResetToken.DoesNotExist:
        messages.error(request, "Invalid or expired reset link.")
        return redirect('forgot_password')

    if reset_token.is_expired() or reset_token.is_used:
        messages.error(request, "Reset link expired or already used.")
        return redirect('forgot_password')

    if request.method == "POST":
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            reset_token.user.password = make_password(new_password)
            reset_token.user.save()

            reset_token.is_used = True
            reset_token.save()

            messages.success(request, "Password reset successful! You can now log in.")
            return redirect('login_view')
    else:
        form = ResetPasswordForm()

    return render(request, 'reset_password.html', {'form': form})