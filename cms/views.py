from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.template import Context, loader, RequestContext
from cms.models import Daily, Comment
from cms.forms import DailyForm, CommentForm, SearchForm
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib import auth


# 日報の一覧
@login_required
def daily_list(request):
    """日報の一覧"""
    # return HttpResponse('日報の一覧')
    # 表示する日報のリストを取得
    # 最初に呼び出されるビューなので日報すべてを日付順に取得
    dailys = Daily.objects.all().filter(release=True).order_by('date')   # 表示する日報のリストを取得
    # 検索フォームを生成
    form = SearchForm()

    return render(request,
                  'cms/daily_list.html',                   # 使用するテンプレート
                  {'form': form, 'dailys': dailys})         # テンプレートに渡すデータ・フォーム


@login_required
def daily_detail(request, daily_id):
    daily = get_object_or_404(Daily, pk=daily_id)
    comments = daily.comment.all().order_by('date')  # 日報の子供の、コメントを読む
    form = SearchForm()

    comment = Comment(user=request.user)
    if request.method == 'POST':
        comment_form = CommentForm(request.POST, instance=comment)  # POST された request データからフォームを作成
        if form.is_valid():  # フォームのバリデーション
            comment = form.save(commit=False)
            comment.daily = daily  # このコメントの、親のコメントをセット
            comment.save()
    else:  # GET の時
        comment_form = CommentForm(instance=comment)  # impression インスタンスからフォームを作成

    return render(request,
                  'cms/daily_detail.html',
                  {'commentForm': comment_form,'form': form, 'daily': daily, 'comments': comments})

'''
# 日報の詳細画面のクラス
class daily_detail(DetailView):
    # 表示対象となるモデルの指定
    model = Daily
    # 表示に使用するテンプレートを指定
    template_name = 'cms/daily_detail.html'

'''


# 日報の編集
def daily_edit(request, daily_id=None):
    """日報の編集"""
    if daily_id:   # id が指定されている (修正時)
        daily = get_object_or_404(Daily, pk=daily_id)
        if daily.user != request.user:      # 投稿者とログインユーザが異なる場合
            return redirect('login')
    else:         # id が指定されていない (追加時)
        daily = Daily(user=request.user)    # 編集をリクエストしたユーザーの情報を登録し、新規作成

    if request.method == 'POST':
        form = DailyForm(request.POST, instance=daily)  # POST された request データからフォームを作成
        if form.is_valid():    # フォームのバリデーション
            daily = form.save(commit=False)
            if 'release' in request.POST:
                daily.release = True
            daily.save()    # 日報の登録
            return redirect('cms:daily_detail', daily_id=daily.id)
    else:    # GET の時
        form = DailyForm(instance=daily)  # book インスタンスからフォームを作成

    return render(request, 'cms/daily_edit.html', dict(form=form, daily_id=daily_id))


# 日報の削除
# アラート表示などは未実装
def daily_del(request, daily_id):
    """日報の削除"""
    daily = get_object_or_404(Daily, pk=daily_id)
    if daily.user != request.user:  # 投稿者とログインユーザが異なる場合
        return redirect('login')
    daily.delete()  # 日報の削除
    return redirect('cms:daily_list')   # 一覧画面にリダイレクト


# 日報の検索
def daily_search(request):
    # リクエストが送られてきている場合
    if request.method == 'POST':
        # リクエストを取得しながら検索フォームを生成
        form = SearchForm(request.POST)
        # フォームの中身が存在する場合=検索キーワードが入力されている場合
        if form.is_valid():
            tpl = loader.get_template('cms/daily_list.html')
            # 検索対象中にキーワードが存在するか検索
            # filterを使用、複数条件検索のためQを使用
            dailys = Daily.objects.all().filter(Q(user__username__contains=form.cleaned_data['keyword']) |
                                                Q(title__contains=form.cleaned_data['keyword']) |
                                                Q(report__contains=form.cleaned_data['keyword'])).order_by('date')
            return HttpResponse(tpl.render(RequestContext(request, {'form': form, 'dailys': dailys})))
        else:
            form = SearchForm()
        tpl = loader.get_template('cms/daily_list.html')
        return HttpResponse(tpl.render(RequestContext(request, {'form': form})))


def user_info(request, user_id):
    dailys = Daily.objects.filter(user=user_id).order_by('date')  # 表示する日報のリストを取得
    # 検索フォームを生成
    form = SearchForm()
    userinfo = get_object_or_404(auth.get_user_model(), pk=user_id)

    return render(request,
                  'cms/daily_list.html',  # 使用するテンプレート
                  {'form': form, 'dailys': dailys, 'userinfo': userinfo})  # テンプレートに渡すデータ・フォーム


class comment_list(ListView):
    """コメントの一覧"""
    context_object_name = 'comments'
    template_name = 'cms/comment_list.html'
    # paginate_by = 2  # １ページは最大2件ずつでページングする

    def get(self, request, *args, **kwargs):
        daily = get_object_or_404(Daily, pk=kwargs['daily_id'])  # 親の日報を読む
        comments = daily.comment.all().order_by('date')  # 日報の子供の、コメントを読む
        self.object_list = comments

        context = self.get_context_data(object_list=self.object_list, daily=daily)
        return self.render_to_response(context)


# コメントの編集
def comment_edit(request, daily_id, comment_id=None):
    """感想の編集"""
    daily = get_object_or_404(Daily, pk=daily_id)  # 親の日報を読む
    if comment_id:   # comment_id が指定されている (修正時)
        comment = get_object_or_404(Comment, pk=comment_id)
    else:               # comment_id が指定されていない (追加時)
        comment = Comment(user=request.user)

    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)  # POST された request データからフォームを作成
        if form.is_valid():    # フォームのバリデーション
            comment = form.save(commit=False)
            comment.daily = daily  # このコメントの、親のコメントをセット
            comment.save()
            return redirect('cms:daily_detail', daily_id=daily.id)
    else:    # GET の時
        form = CommentForm(instance=comment)  # impression インスタンスからフォームを作成

    return render(request,
                  'cms/comment_edit.html',
                  dict(form=form, daily_id=daily_id, comment_id=comment_id))


def comment_del(request, daily_id, comment_id):
    """感想の削除"""
    comment = get_object_or_404(Comment, pk=comment_id)
    comment.delete()
    return redirect('cms:comment_list', daily_id=daily_id)