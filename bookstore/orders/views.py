from django,shortcuts import render,redirect
from django.core.urlresolvers import reverse
from utils.decorators import login_required
from django.http import HttpResponse,JsonResponse
from users.models import Address
from order.models import Books
from django_redis import get_redis_connection
from datetime import datetime
from django.conf import settings
import os
import time

@login_required
def order_place(request):
    books_ids = request.POST.getlist('books_ids')
    if not all(books_ids):
        return redirect(reverse('cart:show'))
    passport_id = request.session.get('passport_id')
    addr = Address.objects.get_default_address(passport_id=passport_id)
    books_li = []
    total_count = 0
    total_price = 0
    conn = get_redis_connection('default')
    cart_key = 'cart_%d'%passport_id
    
    for id in books_ids:
        books = Books.objects.get_books_by_id(books_id=id)
        count = conn.hget(cart_key,id)
        books.count = count
        amount = int(count)*books_price
        books.amount = amount
        books_li.append(books)
        total_count += int(count)
        total_price += books.amount
    transit_price = 10
    total_price = total_price + transit_price
    books_ids = ','.join(books_ids)
    context = {
        'addr':addr,
        'books_li':books_li,
        'total_price':total_price,
        'total_count':total_count,
        'transit_price':transit_price,
        'total_pay':total_pay,
        'books_ids':books_ids,
    }
    return render(request,'order/place_order.html',context)

