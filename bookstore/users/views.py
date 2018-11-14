from django.shortcuts import render,redirect,reverse
from utils.decorators import login_required
import re
from django.core.paginator import Paginator
# Create your views here.
def register(request):
    return render(request,'users/register.html')


def register_handle(request):
    username=request.POST.get('user_name')
    password=request.POST.get('pwd')
    email=request.POST.get('email')

    if not all([username,password,email]):
        return render(request,'users/register.html',{'errmsg':'参数不能为空!'})
    
    if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$',email):
        return render(request,'users/register.html',{'errmsg':'邮箱不合法！'})
    try:
        Passport.objects.add_one_passport(username=username,password=password,email=email)
    except:
        return render(request,'users/register.html',{'errmsg':'用户名已存在！'})
#    return redirect(reverse('user:register'))
    return redirect(reverse('books:index'))

def login(request):
    if request.COOKIES.get('username'):
        username=request.COOKIES.get('username')
        checked='checked'
    else:
        username=''
        checked=''
    context={
        'username':username,
        'checked':checked,
    }
    return render(request,'users/login.html',context)
        
def login_check(request):
    username=request.POST.get('username')
    password=request.POST.get('password')
    remeber=request.POST.get('remeber')
    if not all([username,password,remember]):
        return JsonResponse({'res':2})
    passport=Passport.objects.get_one_passport(username=username,password=password)
    if passort:
        next_url=reverse('books:index')
        jres=JsonResponse({'res':1,'next_url':next_url})
        if remember=='true':
            jres.set_cookie('username',username,max_age=7*24*3600)
        else:
            jres.delete_cookie('username')
        request.session['islogin']=True
        request.session['username']=username
        request.session['passport_id']=passport.id
        return jres
    else:
        return JsonResponse({'res':0})

def logout(request):
    request.session.flush()
    return redirect(reverse('books:index'))

@login_required
def user(request):
    passport_id=request.session.get('passport_id')
    addr = Address.objects.get_default_address(passport_id=passport_id)
    books_li = []
    context = {
        'addr':addr,
        'page':'user',
        'books_li':books_li
    }
    return render(request,'users/user_center_info.html',context)
@login_required
def address(request):
    passport_id = request.session.get('passport_id')
    if request.method == 'GET':
        addr = Address.objects.get_default_address(passport_id=passport_id)
        return render(request,'user/user_center_site.html',{'addr':addr,'page':'address'})
    else:
        recipient_name = request.POST.get('username')
        recipient_addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        recipient_phone = request.POST.get('phone')
        if not all([recipient_name,recipient_addr,recipient_phone,zip_code]):
            return render(request,'users/user_center_site.html',{'errmsg':'参数不能为空!'})
        Address.objects.add_one_address(passport_id=passport_id,
                                        recipient_name=recipient_name,
                                        recipient_addr=recipient_addr,
                                        recipient_phone=recipient_phone,
                                        zip_code=zip_code)
        return redirect(reverse('user:address'))
@login_required
def order(request, page):
    passport_id = request.session.get('passport_id')

    order_li = OrderInfo.objects.filter(passport_id=passport_id)

    for order in order_li:
        order_id = order.order_id
        order_books_li = OrderGoods.objects.filter(order_id=order_id)

        for order_books in order_books_li:
            count = order_books.count
            price = order_books.price
            amount = count * price
            order_books.amount = amount

        order.order_books_li = order_books_li
    
    paginator = Paginator(order_li, 3)      # 每页显示3个订单
    
    num_pages = paginator.num_pages
    
    if not page:        # 首次进入时默认进入第一页
        page = 1
    if page == '' or int(page) > num_pages:
        page = 1
    else:
        page = int(page)
        
    order_li = paginator.page(page)
    
    if num_pages < 5:
        pages = range(1, num_pages + 1)
    elif page <= 3:
        pages = range(1, 6)
    elif num_pages - page <= 2:
        pages = range(num_pages - 4, num_pages + 1)
    else:
        pages = range(page - 2, page + 3)

    context = {
        'order_li': order_li,
        'pages': pages,
    }

    return render(request, 'users/user_center_order.html', context)
