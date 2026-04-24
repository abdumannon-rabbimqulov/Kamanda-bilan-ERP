from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from apps.accounts.decorators import role_required
from .models import RewardItem, Redemption
from apps.accounts.models import User
from apps.courses.models import Enrollment

@login_required
@role_required('student')
def shop_list(request):
    items = RewardItem.objects.filter(is_active=True, stock_quantity__gt=0)
    user_redemptions = Redemption.objects.filter(student=request.user).order_by('-created_at')
    return render(request, 'rewards/shop.html', {
        'items': items,
        'user_redemptions': user_redemptions
    })

@login_required
@role_required('student')
def leaderboard(request):
    # Umumiy reyting
    global_top = User.objects.filter(role='student').order_by('-xp')[:50]
    
    # Guruhim bo'yicha reyting
    my_group_top = []
    enrollment = Enrollment.objects.filter(student=request.user).first()
    if enrollment:
        group = enrollment.group
        my_group_top = User.objects.filter(
            enrollment__group=group, 
            role='student'
        ).order_by('-xp').distinct()

    return render(request, 'rewards/leaderboard.html', {
        'global_top': global_top,
        'my_group_top': my_group_top,
        'current_group': enrollment.group if enrollment else None
    })

@login_required
@role_required('student')
def redeem_item(request, item_id):
    item = get_object_or_404(RewardItem, id=item_id, is_active=True)
    user = request.user

    if user.coins < item.coin_price:
        messages.error(request, "Sizda coinlar yetarli emas.")
        return redirect('rewards:shop')

    if item.stock_quantity <= 0:
        messages.error(request, "Ushbu buyum tugab qolgan.")
        return redirect('rewards:shop')

    # Deduct coins and stock
    user.coins -= item.coin_price
    user.save()

    item.stock_quantity -= 1
    item.save()

    Redemption.objects.create(
        student=user,
        item=item,
        coins_spent=item.coin_price
    )

    messages.success(request, f"Tabriklaymiz! {item.name} muvaffaqiyatli xarid qilindi. Tez orada adminlar siz bilan bog'lanishadi.")
    return redirect('rewards:shop')

@role_required('admin')
def admin_reward_list(request):
    items = RewardItem.objects.all().order_by('-created_at')
    redemptions = Redemption.objects.all().select_related('student', 'item').order_by('-created_at')
    
    if request.method == 'POST' and 'add_item' in request.POST:
        name = request.POST.get('name')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        desc = request.POST.get('desc', '')
        image = request.FILES.get('image')
        
        RewardItem.objects.create(
            name=name,
            coin_price=price,
            stock_quantity=stock,
            description=desc,
            image=image
        )
        messages.success(request, "Yangi buyum qo'shildi.")
        return redirect('rewards:admin_list')

    return render(request, 'rewards/admin_list.html', {
        'items': items,
        'redemptions': redemptions
    })

@role_required('admin')
def edit_reward(request, pk):
    item = get_object_or_404(RewardItem, pk=pk)
    if request.method == 'POST':
        item.name = request.POST.get('name')
        item.coin_price = request.POST.get('price')
        item.stock_quantity = request.POST.get('stock')
        item.description = request.POST.get('desc', '')
        image = request.FILES.get('image')
        if image:
            item.image = image
        item.is_active = request.POST.get('is_active') == 'on'
        item.save()
        messages.success(request, f"{item.name} muvaffaqiyatli yangilandi.")
        return redirect('rewards:admin_list')
    return redirect('rewards:admin_list')

@role_required('admin')
def delete_reward(request, pk):
    item = get_object_or_404(RewardItem, pk=pk)
    name = item.name
    item.delete()
    messages.success(request, f"{name} o'chirildi.")
    return redirect('rewards:admin_list')

@role_required('admin')
def update_redemption_status(request, redemption_id):
    redemption = get_object_or_404(Redemption, id=redemption_id)
    status = request.POST.get('status')
    if status in dict(Redemption.STATUS):
        redemption.status = status
        redemption.save()
        messages.success(request, "Status yangilandi.")
    return redirect('rewards:admin_list')
