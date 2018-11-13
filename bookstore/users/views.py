from django.shortcuts import render,redirect,reverse
from utils.decorators import login_required
import re
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

