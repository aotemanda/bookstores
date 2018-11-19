from django.shortcuts import render,redirect,reverse
from utils.decorators import login_required
import re
from django.core.paginator import Paginator
from orders.models import OrderInfo,OrderGoods
from users.models import Passport,Address
from django.http import JsonResponse,HttpResponse
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from users.tasks import send_active_email
from django.conf import settings
import os
from django.core.mail import send_mail
from django_redis import get_redis_connection
from books.models import Books
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

    p = Passport.objects.check_passport(username=username)

    if p:
        return render(request, 'users/register.html', {'errmsg': '用户名已存在！'})
    passport = Passport.objects.add_one_passport(username=username, password=password, email=email)

    
    serializer = Serializer(settings.SECRET_KEY, 3600)
    token = serializer.dumps({'confirm':passport.id}) 
    token = token.decode()

    send_mail('书城用户激活', '', settings.EMAIL_FROM, [email], html_message='<a href="http://127.0.0.1:8000/user/active/%s/">http://127.0.0.1:8000/user/active/</a>' % token)

    #send_active_email.delay(token,username,email)
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
    remember=request.POST.get('remember')
    verifycode = request.POST.get('verifycode')

    if not all([username,password,remember, verifycode]):
        return JsonResponse({'res':2})
    if verifycode.upper() != request.session['verifycode']:
        return JsonResponse({'res': 2})


    passport=Passport.objects.get_one_passport(username=username,password=password)
    if passport:
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
    con = get_redis_connection('default')
    key = 'history_%d' % passport_id
    # 取出用户最近浏览的5个商品的id
    history_li = con.lrange(key, 0, 4)
    # history_li = [21,20,11]
    # print(history_li)
    # 查询数据库,获取用户最近浏览的商品信息
    # books_li = Books.objects.filter(id__in=history_li)
    books_li = []
    for id in history_li:
        books = Books.objects.get_books_by_id(books_id=id)
        books_li.append(books)

    return render(request, 'users/user_center_info.html', {'addr': addr,
                                                           'page': 'user',
                                                           'books_li': books_li})

@login_required
def address(request):
    passport_id = request.session.get('passport_id')
    if request.method == 'GET':
        addr = Address.objects.get_default_address(passport_id=passport_id)
        return render(request,'users/user_center_site.html',{'addr':addr,'page':'address'})
    else:
        recipient_name = request.POST.get('username')
        recipient_addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        #print(zip_code)
        recipient_phone = request.POST.get('phone')
        if not all([recipient_name,recipient_addr,recipient_phone,zip_code]):
            return render(request,'users/user_center_site.html',{'errmsg':'参数不能为空!'})
        Address.objects.add_one_address(
                                        passport_id=passport_id,
                                        recipient_name=recipient_name,
                                        recipient_addr=recipient_addr,
                                        recipient_phone=recipient_phone,
                                        zip_code=zip_code,
                                            )
        return redirect(reverse('user:address'))
@login_required
def order(request, page):
    passport_id = request.session.get('passport_id')

    order_li = OrderInfo.objects.filter(passport_id=passport_id)

    for order in order_li:
        order_id = order.order_id
        order_books_li = OrderGoods.objects.filter(order_id=order_id)
        #print(order_books_li)
        for order_books in order_books_li:
            count = order_books.count
            price = order_books.price
            amount = count * price
            order_books.amount = amount
            #print(count)
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


def verifycode(request):
    #引入绘图模块
    from PIL import Image, ImageDraw, ImageFont
    #引入随机函数模块
    import random
    #定义变量，用于画面的背景色、宽、高
    bgcolor = (random.randrange(20, 100), random.randrange(
        20, 100), 255)
    width = 100
    height = 25
    #创建画面对象
    im = Image.new('RGB', (width, height), bgcolor)
    #创建画笔对象
    draw = ImageDraw.Draw(im)
    #调用画笔的point()函数绘制噪点
    for i in range(0, 100):
        xy = (random.randrange(0, width), random.randrange(0, height))
        fill = (random.randrange(0, 255), 255, random.randrange(0, 255))
        draw.point(xy, fill=fill)
    #定义验证码的备选值
    str1 = 'ABCD123EFGHIJK456LMNOPQRS789TUVWXYZ0'
    #随机选取4个值作为验证码
    rand_str = ''
    for i in range(0, 4):
        rand_str += str1[random.randrange(0, len(str1))]
    #构造字体对象
    font = ImageFont.truetype(os.path.join(settings.BASE_DIR, "Ubuntu-RI.ttf"), 15)
    #构造字体颜色
    fontcolor = (255, random.randrange(0, 255), random.randrange(0, 255))
    #绘制4个字
    draw.text((5, 2), rand_str[0], font=font, fill=fontcolor)
    draw.text((25, 2), rand_str[1], font=font, fill=fontcolor)
    draw.text((50, 2), rand_str[2], font=font, fill=fontcolor)
    draw.text((75, 2), rand_str[3], font=font, fill=fontcolor)
    #释放画笔
    del draw
    #存入session，用于做进一步验证
    request.session['verifycode'] = rand_str
    #内存文件操作
    import io
    buf = io.BytesIO()
    #将图片保存在内存中，文件类型为png
    im.save(buf, 'png')
    #将内存中的图片数据返回给客户端，MIME类型为图片png
    return HttpResponse(buf.getvalue(), 'image/png')

def register_active(request, token):
    '''用户账户激活'''
    serializer = Serializer(settings.SECRET_KEY, 3600)
    try:
        info = serializer.loads(token)
        passport_id = info['confirm']
        # 进行用户激活
        passport = Passport.objects.get(id=passport_id)
        passport.is_active = True
        passport.save()
        # 跳转的登录页
        return redirect(reverse('user:login'))
    except SignatureExpired:
        # 链接过期
        return HttpResponse('激活链接已过期')

