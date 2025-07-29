from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Sum
from .models import LoyaltyPoint, Reward, PromoCode
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone

class LoyaltyDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'marketing/loyalty_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['points'] = LoyaltyPoint.objects.filter(user=self.request.user).aggregate(total=Sum('points'))['total'] or 0
        context['rewards'] = Reward.objects.filter(is_active=True)
        return context

@login_required
def dashboard_view(request):
    context = {
        'total_points': LoyaltyPoint.objects.aggregate(total=Sum('points'))['total'] or 0,
        'total_uses': PromoCode.objects.aggregate(total=Sum('uses'))['total'] or 0,
        'active_codes': PromoCode.objects.filter(valid_to__gte=timezone.now()).count(),
    }
    return render(request, 'admin/dashboard.html', context)