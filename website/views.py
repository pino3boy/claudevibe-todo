import calendar
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Task
from .forms import UserUpdateForm


def _add_bootstrap_classes(form):
    for field in form.fields.values():
        existing = field.widget.attrs.get('class', '')
        field.widget.attrs['class'] = (existing + ' form-control').strip()
    return form


def _int_param(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@login_required
def home(request):
    today = date.today()
    year = _int_param(request.GET.get('year'), today.year)
    month = _int_param(request.GET.get('month'), today.month)

    # Clamp to valid month range
    year = max(2000, min(year, 2100))
    month = max(1, min(month, 12))

    month_name = calendar.month_name[month]
    cal_weeks = calendar.monthcalendar(year, month)

    prev_month = month - 1 or 12
    prev_year = year - 1 if month == 1 else year
    next_month = month % 12 + 1
    next_year = year + 1 if month == 12 else year

    # Days in this month that already have at least one task
    task_dates = set(
        Task.objects.filter(user=request.user, date__year=year, date__month=month)
        .values_list('date__day', flat=True)
    )

    # Days in this month with a past, incomplete task (general or scheduled)
    overdue_dates = set(
        Task.objects.filter(
            user=request.user, date__year=year, date__month=month,
            date__lt=today, completed=False,
        ).values_list('date__day', flat=True)
    )

    return render(request, 'home.html', {
        'cal_weeks': cal_weeks,
        'month_name': month_name,
        'year': year,
        'month': month,
        'today': today,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'task_dates': task_dates,
        'overdue_dates': overdue_dates,
    })


def _format_hour(h):
    if h == 12:
        return "12:00 PM"
    elif h < 12:
        return f"{h}:00 AM"
    else:
        return f"{h - 12}:00 PM"


SCHEDULE_HOURS = range(5, 23)  # 5 AM to 10 PM


@login_required
def day_view(request, year, month, day):
    target_date = date(year, month, day)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'add_task':
            text = request.POST.get('text', '').strip()
            if text:
                Task.objects.create(user=request.user, date=target_date, hour=None, text=text)

        elif form_type == 'save_schedule':
            for h in SCHEDULE_HOURS:
                text = request.POST.get(f'hour_{h}', '').strip()
                completed = request.POST.get(f'done_{h}') == 'on'
                if text:
                    Task.objects.update_or_create(
                        user=request.user, date=target_date, hour=h,
                        defaults={'text': text, 'completed': completed},
                    )
                else:
                    Task.objects.filter(user=request.user, date=target_date, hour=h).delete()

            messages.success(request, 'Saved')

        return redirect('day', year=year, month=month, day=day)

    general_tasks = Task.objects.filter(user=request.user, date=target_date, hour__isnull=True)
    hourly_map = {
        t.hour: (t.text, t.completed)
        for t in Task.objects.filter(user=request.user, date=target_date, hour__isnull=False)
    }
    is_past_day = target_date < date.today()
    schedule = []
    for h in SCHEDULE_HOURS:
        text, completed = hourly_map.get(h, ('', False))
        overdue = is_past_day and bool(text) and not completed
        schedule.append((h, _format_hour(h), text, completed, overdue))

    return render(request, 'day.html', {
        'target_date': target_date,
        'general_tasks': general_tasks,
        'schedule': schedule,
        'year': year,
        'month': month,
        'day': day,
    })


@login_required
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    year, month, day = task.date.year, task.date.month, task.date.day
    if request.method == 'POST':
        task.delete()
    return redirect('day', year=year, month=month, day=day)


@login_required
def profile(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'update_info':
            info_form = UserUpdateForm(request.POST, instance=request.user)
            pwd_form = PasswordChangeForm(request.user)
            if info_form.is_valid():
                info_form.save()
                messages.success(request, 'Profile updated successfully.')
                return redirect('profile')

        elif form_type == 'change_password':
            info_form = UserUpdateForm(instance=request.user)
            pwd_form = PasswordChangeForm(request.user, request.POST)
            if pwd_form.is_valid():
                user = pwd_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password changed successfully.')
                return redirect('profile')

        else:
            info_form = UserUpdateForm(instance=request.user)
            pwd_form = PasswordChangeForm(request.user)

    else:
        info_form = UserUpdateForm(instance=request.user)
        pwd_form = PasswordChangeForm(request.user)

    return render(request, 'profile.html', {
        'info_form': _add_bootstrap_classes(info_form),
        'pwd_form': _add_bootstrap_classes(pwd_form),
    })


def register_user(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully.')
            return redirect('home')
    else:
        form = UserCreationForm()

    return render(request, 'register.html', {'form': _add_bootstrap_classes(form)})


def login_user(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': _add_bootstrap_classes(form)})


def logout_user(request):
    logout(request)
    return redirect('login')
