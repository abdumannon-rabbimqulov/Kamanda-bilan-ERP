from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from apps.accounts.decorators import role_required
from .models import RewardItem, Redemption

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
def update_redemption_status(request, redemption_id):
    redemption = get_object_or_404(Redemption, id=redemption_id)
    status = request.POST.get('status')
    if status in dict(Redemption.STATUS):
        redemption.status = status
        redemption.save()
        messages.success(request, "Status yangilandi.")
    return redirect('rewards:admin_list')
