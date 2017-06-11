import json
import HTMLParser
from datetime import datetime

from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict
from django.conf import settings
from django.contrib.auth.models import User 

from .models import *
from .benefits import *
from .forms import *

HEAD_COUNT = {
    'Up to 250': [0, 249],
    '250 to 499': [250, 499],
    '500 to 999': [500, 999],
    '1,000 to 4,999': [1000, 4999],
    '5,000 and Up': [5000, 2000000],
}

MODEL_MAP = {
    'LIFE': Life,
    'STD': STD,
    'LTD': LTD,
    'STRATEGY': Strategy, 
    'VISION': Vision,
    'DENTAL': Dental,
    'MEDICAL': Medical,
    'EMPLOYERS': Employer,
}

get_class = lambda x: globals()[x]


@csrf_exempt
def print_history(request):
    form_param = json.loads(request.body or "{}")
    limit = int(form_param.get('rowCount'))
    page = int(form_param.get('current'))
    qs_ph = PrintHistory.objects.filter(user=request.user)
    total = qs_ph.count()
    ph_list = []

    for ph in qs_ph:
        benefit = ph.benefit if ph.benefit != 'MEDICALRX' else 'MEDICAL'
        model = MODEL_MAP[benefit]
        plan_name = ''
        if ph.plan:
            if benefit != 'STRATEGY':
                plan_name = model.objects.get(id=ph.plan).title
            else:
                plan_name = model.objects.get(id=ph.plan).employer.name

        plan_type = ph.plan_type if ph.plan_type != 'None' else ''
        ph_ = {
            'id': ph.id,
            'benefit': ph.benefit,
            'plan_name': plan_name,
            'plan_type': plan_type,
            'print_date': ph.print_date.strftime('%Y-%m-%d %H:%M:%S')
        }
        ph_list.append(ph_)

    return JsonResponse({
        "current": page,
        "rowCount": limit,
        "rows": ph_list,
        "total": total
        }, safe=False)


@login_required(login_url='/login')
def edit_print_history(request, id):
    ph = PrintHistory.objects.get(id=id)
    request.session['bnchmrk_benefit'] = ph.benefit
    request.session['plan'] = ph.plan
    request.session['plan_type'] = ph.plan_type
    request.session['ft_industries'] = json.loads(ph.ft_industries)
    request.session['ft_head_counts'] = json.loads(ph.ft_head_counts)
    request.session['ft_regions'] = json.loads(ph.ft_regions)
    request.session['ft_states'] = json.loads(ph.ft_states)
    request.session['ft_other'] = json.loads(ph.ft_other)
    request.session[ph.benefit+'_quintile_properties'] = json.loads(ph.properties)
    request.session[ph.benefit+'_quintile_properties_inv'] = json.loads(ph.properties_inv)
    request.session[ph.benefit+'_services'] = json.loads(ph.services)
    return HttpResponseRedirect('/benchmarking/'+ph.benefit.lower())


@csrf_exempt
@login_required(login_url='/login')
def enterprise(request):
    """
    POST: for Home bootgrid table
    """
    if request.method == 'POST':
        form_param = json.loads(request.body or "{}")
        limit = int(form_param.get('rowCount'))
        page = int(form_param.get('current'))
        ft_industries = form_param.get('industry_') or ['*']
        ft_head_counts = form_param.get('head_counts') or ['0-2000000']
        ft_other = form_param.get('others')
        ft_regions = form_param.get('regions')
        ft_states = form_param.get('states')
        q = form_param.get('q', '')
        threshold = form_param.get('threshold', 1)
        is_print = form_param.get('print')

        if is_print:
            ft_industries_label = form_param.get('industry_label')
            ft_head_counts_label = form_param.get('head_counts_label')
            ft_other_label = form_param.get('others_label')
            ft_regions_label = form_param.get('regions_label')
            ft_states_label = form_param.get('states_label')

            # store for print
            request.session['ft_industries'] = ft_industries
            request.session['ft_head_counts'] = ft_head_counts
            request.session['ft_other'] = ft_other
            request.session['ft_regions'] = ft_regions
            request.session['ft_states'] = ft_states

            request.session['ft_industries_label'] = ft_industries_label
            request.session['ft_head_counts_label'] = ft_head_counts_label
            request.session['ft_other_label'] = ft_other_label
            request.session['ft_regions_label'] = ft_regions_label
            request.session['ft_states_label'] = ft_states_label

            for benefit in MODEL_MAP.keys():
                if benefit == 'MEDICAL':
                    benefit = 'MEDICALRX'
                request.session[benefit+'_quintile_properties'] = None
                request.session[benefit+'_quintile_properties_inv'] = None
                request.session[benefit+'_services'] = None

        lstart = (page - 1) * limit
        lend = lstart + limit

        group = request.user.groups.first().name

        employers, num_companies = get_filtered_employers(ft_industries, 
                                                          ft_head_counts, 
                                                          ft_other, 
                                                          ft_regions, 
                                                          ft_states,
                                                          lstart, 
                                                          lend,
                                                          group,
                                                          q,
                                                          threshold)

        # convert head-count into groups
        employers_ = []
        for item in employers:
            item_ = model_to_dict(item)

            # if group != 'bnchmrk':
            #     item_['name'] = item.new_name

            item__ = []
            if item.nonprofit:
                item__.append('Non-Profit')
            if item.govt_contractor:
                item__.append("Gov't Contractor")
            item_['other'] = '@'.join(item__)

            item__ = []
            if item.industry1:
                item__.append(item.industry1)
            if item.industry2:
                item__.append(item.industry2)
            if item.industry3:
                item__.append(item.industry3)
            item_['industry'] = '@'.join(item__)

            item__ = []
            if item.new_england:
                item__.append('New England')
            if item.mid_atlantic:
                item__.append('Tri-State Area')
            if item.south_atlantic:
                item__.append('South Atlantic')
            if item.south_cental:
                item__.append('South Central')
            if item.east_central:
                item__.append('East North Central')
            if item.west_central:
                item__.append('West North Central')
            if item.mountain:
                item__.append('Mountian')
            if item.pacific:
                item__.append('Pacific')
            item_['region'] = '@'.join(item__)

            item_['r_size'] = item.size
            for key, val in HEAD_COUNT.items():
                if item.size in range(val[0], val[1]):
                    item_['size'] = key
                    break

            item_['industry'] = item.industry1
            employers_.append(item_)

        if num_companies < settings.EMPLOYER_THRESHOLD and threshold:
            num_companies = 0

        return JsonResponse({
            "current": page,
            "rowCount": limit,
            "rows": employers_,
            "total": num_companies
            }, safe=False)
        

@csrf_exempt
def faq(request):
    """
    POST: for faq bootgrid table
    """
    form_param = json.loads(request.body or "{}")
    limit = int(form_param.get('rowCount'))
    page = int(form_param.get('current'))
    q = form_param.get('q', '')
    category = form_param.get('category', '')

    lstart = (page - 1) * limit
    lend = lstart + limit

    faqs = []
    faq_qs = FAQ.objects.filter(Q(title__icontains=q) | Q(content__icontains=q))

    if category:
        faq_qs = faq_qs.filter(category=category)

    for faq in faq_qs[lstart:lend]:
        faqs.append({ 'title': faq.title, 
                      'content': faq.content[:50], 
                      'category': faq.category.title,
                      'created_at': datetime.strftime(faq.created_at, '%d/%m/%Y %H:%M'),
                      'id': faq.id})

    return JsonResponse({
        "current": page,
        "rowCount": limit,
        "rows": faqs,
        "total": faq_qs.count()
        }, safe=False)


def faq_detail(request, id):
    faq = FAQ.objects.filter(id=id).first()
    if not faq:
        return render(request, 'error/404.html')

    return render( request, 'faq_detail.html', locals())

    
@csrf_exempt
def update_properties(request):
    form_param = request.POST
    benefit = form_param.get('benefit')
    plan = int(form_param.get('plan') or '0')
    quintile_properties = form_param.getlist('quintile_properties[]')
    quintile_properties_inv = form_param.getlist('quintile_properties_inv[]')
    services = form_param.getlist('services[]')
    print_template = form_param.get('print_template')

    plan_type = request.session.get('plan_type')
    # save for print
    if plan != -1:
        request.session['plan'] = plan
        request.session[benefit+'_quintile_properties'] = quintile_properties  
        request.session[benefit+'_quintile_properties_inv'] = quintile_properties_inv  
        request.session[benefit+'_services'] = services  
    else:
        plan = request.session['plan']
        quintile_properties = request.session.get(benefit+'_quintile_properties')
        quintile_properties_inv = request.session.get(benefit+'_quintile_properties_inv')
        services = request.session.get(benefit+'_services')

    if benefit == 'MEDICALRX':
        benefit = 'MEDICAL'

    if not int(plan):
        return HttpResponse('') 
    else:
        func_name = 'get_{}_properties'.format(benefit.lower())
        return globals()[func_name](request, plan, plan_type, quintile_properties, quintile_properties_inv, services)


@csrf_exempt
def update_quintile(request):
    benefit = request.session.get('bnchmrk_benefit')
    plan_type = request.session.get('plan_type')
    
    form_param = request.POST
    attr = form_param.get('property')
    type_ = form_param.get('type')
    inverse = form_param.get('inverse')
    plan = int(form_param.get('plan') or '-1')

    quintile_properties = form_param.getlist('quintile_properties[]')
    quintile_properties_inv = form_param.getlist('quintile_properties_inv[]')
    services = form_param.getlist('services[]')

    request.session[benefit+'_quintile_properties'] = quintile_properties  
    request.session[benefit+'_quintile_properties_inv'] = quintile_properties_inv  
    request.session[benefit+'_services'] = services  

    employers, num_companies = get_filtered_employers_session(request)
    quintile, qscore, value = get_attr_quintile(benefit, employers, num_companies, plan_type, attr, MODEL_MAP, plan, inverse=='true')

    return JsonResponse({
        'graph': quintile,
        'qscore': qscore,
        'val': value,
        'property': attr,
        'type': type_}, safe=False)


@csrf_exempt
def update_e_cost(request):
    form_param = request.POST
    benefit = form_param.get('benefit')
    plan_type = form_param.get('plan_type')
    service = form_param.get('service')    
    plan = int(form_param.get('plan') or '-1')

    quintile_properties = form_param.getlist('quintile_properties[]')
    quintile_properties_inv = form_param.getlist('quintile_properties_inv[]')
    services = form_param.getlist('services[]')

    request.session[benefit+'_quintile_properties'] = quintile_properties  
    request.session[benefit+'_quintile_properties_inv'] = quintile_properties_inv  
    request.session[benefit+'_services'] = services  

    employers, num_companies = get_filtered_employers_session(request)

    plan_type = get_real_medical_type(plan_type)
    qs = Medical.objects.filter(employer__in=employers, type__in=plan_type) 
    e_costs, e_stacks = employee_pricing_medical(qs, service)
    val, idx = get_median_list(e_costs)

    instance = Medical.objects.filter(id=plan).first()
    if instance:
        val, _ = employee_pricing_medical([instance], service)
        percentile_array = get_incremental_array_(len(e_costs), sorted(e_costs))

        val = val[0] if val else None
        rank = get_rank(percentile_array, val)
        if rank != '-':
            rank = 100 - rank
    else:
        rank = 'N/A'

    result = e_stacks[idx]
    result.append(rank)
    return JsonResponse(result, safe=False) 


@csrf_exempt
def get_num_employers(request):
    employers, num_companies = get_filtered_employers_session(request)
    return HttpResponse('{:,.0f}'.format(num_companies))


@csrf_exempt
def get_plans(request):
    benefit = request.POST.get('benefit')
    plan_type = request.POST.get('plan_type')

    group = request.user.groups.first().name

    if benefit == 'MEDICALRX':
        benefit = 'MEDICAL'

    plans = get_plans_(benefit, group, plan_type)
    return render(request, 'includes/plans.html', { 'plans': plans })


def get_plans_(benefit, group, plan_type):
    model = MODEL_MAP[benefit]
    if group == 'bnchmrk':
        objects = model.objects.all()
    else:
        objects = model.objects.filter(employer__broker=group)

    if plan_type in ['DPPO', 'DMO']:     # for DPPO, DMO pages
        objects = objects.filter(type=plan_type)
    elif plan_type == 'PPO':
        objects = objects.filter(type__in=['PPO', 'POS'])
    elif plan_type == 'HDHP':
        objects = objects.filter(type='HDHP')
    elif plan_type == 'HMO':
        objects = objects.filter(type__in=['HMO', 'EPO'])
    elif benefit == 'LIFE':
        objects = objects.filter(type=plan_type)

    if benefit in ['LIFE', 'DENTAL', 'MEDICAL']:
        return [
                   [item.id, '{} - {} - {}'.format(item.employer.name, item.type, item.title)]
                   for item in objects.order_by('employer__name', 'title')
               ]#[:10]   # TEST
    elif benefit in ['STD', 'LTD', 'VISION']:
        return [
                   [item.id, '{} - {}'.format(item.employer.name, item.title)]
                   for item in objects.order_by('employer__name', 'title')
               ]
    elif benefit in ['STRATEGY']:
        return [
                   [item.id, '{}'.format(item.employer.name)]
                   for item in objects.order_by('employer__name')
               ]
    elif benefit in ['EMPLOYERS']:
        return [
                   [item.id, '{}'.format(item.name)]
                   for item in objects.order_by('name')
               ]


def support(request):
    categories = FAQCategory.objects.all()
    return render(request, 'support.html', locals())    


@login_required(login_url='/login')
def home(request):
    return render(request, 'index.html', {
            'industries': get_industries(),
            'EMPLOYER_THRESHOLD_MESSAGE': settings.EMPLOYER_THRESHOLD_MESSAGE
        })    


@login_required(login_url='/login')
def accounts(request):            
    group = request.user.groups.first().name
    if group == 'NFP':
        return render(request, 'error/403.html')

    return render(request, 'accounts.html', { 
        'EMPLOYER_THRESHOLD_MESSAGE': settings.EMPLOYER_THRESHOLD_MESSAGE_ACCOUNT,
        'industries': get_industries(),
        'STATES': STATE_CHOICES
    })


@login_required(login_url='/login')
def account_detail(request, id):
    group = request.user.groups.first().name

    employer = Employer.objects.filter(id=id).first()
    if not employer:
        return render(request, 'error/404.html')

    if group != 'bnchmrk' and group != employer.broker or group == 'NFP':
        return render(request, 'error/403.html')

    request.session['benefit'] = request.session.get('benefit', 'MEDICAL')

    regions = []
    if employer.new_england:
        regions.append('New England Region')
    if employer.mid_atlantic:
        regions.append('Mid Atlantic Region')
    if employer.south_atlantic:
        regions.append('South Atlantic Region')
    if employer.south_cental:
        regions.append('South Central Region')
    if employer.east_central:
        regions.append('East Central Region')
    if employer.west_central:
        regions.append('West Central Region')
    if employer.mountain:
        regions.append('Mountain Region')
    if employer.pacific:
        regions.append('Pacific Region')
    region = ', '.join(regions)

    industries = []
    if employer.industry1:
        industries.append(employer.industry1)
    if employer.industry2:
        industries.append(employer.industry2)
    if employer.industry3:
        industries.append(employer.industry3)
    industry = ', '.join(industries)

    plans = []
    for model in [Medical, Dental, Vision, Life, STD, LTD]:
        plans.append((model.__name__, model.objects.filter(employer=employer).count()))

    plans_list = {}
    for model in [Medical, Dental, Vision, Life, STD, LTD, Strategy]:
        plans_list[model.__name__] = []
        for item in model.objects.filter(employer=employer):
            if model == Medical:
                plans_list[model.__name__].append([item.title, item.id, 
                    item.type, get_dollar_property(item.in_ded_single), 
                    get_dollar_property(item.in_max_single)])
            elif model == Dental:
                plans_list[model.__name__].append([item.title, item.id, 
                    item.type, get_dollar_property(item.in_ded_single), 
                    get_dollar_property(item.in_max)])
            elif model == Vision:
                plans_list[model.__name__].append([item.title, item.id, 
                    get_dollar_property(item.exam_copay), 
                    get_dollar_property(item.lenses_copay), 
                    get_dollar_property(item.frames_allowance)])
            elif model == Life:
                plans_list[model.__name__].append([item.title, item.id, 
                    item.type, 
                    get_dollar_property(item.multiple_max), 
                    get_dollar_property(item.flat_amount)])
            elif model == STD:
                plans_list[model.__name__].append([item.title, item.id, 
                    item.waiting_days,
                    get_percent_property(item.percentage), 
                    get_dollar_property(item.weekly_max),])
            elif model == LTD:
                plans_list[model.__name__].append([item.title, item.id, 
                    item.waiting_weeks, get_percent_property(item.percentage), 
                    get_dollar_property(item.monthly_max)])
            else:
                plans_list[model.__name__].append([item.id, item.spousal_surcharge, 
                    item.tobacco_surcharge, item.offer_fsa, item.salary_banding])
                
    return render(request, 'account_detail.html', locals())


@csrf_exempt
def account_detail_benefit(request):
    benefit = request.POST['benefit'];
    plan = request.POST['plan'];
    model = MODEL_MAP[benefit]

    request.session['benefit'] = benefit
    item = model.objects.get(id=plan)

    form = get_class(model.__name__+'Form') 
    forms = {item.id:form(instance=item)}

    bc = BOOLEAN_CHOICES
    dtc = DEN_TYPE_CHOICES
    mtc = MED_TYPE_CHOICES
    mbc = MED_BOOL_CHOICES
    ltc = LIFE_TYPE_CHOICES
    ccc = COSTSHARE_CHOICES
    sbc = STRATEGY_BOOLEAN_CHOICES

    include_path = "account_detail/form/{}.html".format(benefit.lower())
    template = 'account_detail/benefit.html'
    return render(request, template, locals())


@csrf_exempt
def update_benefit(request, instance_id):
    employer_id = request.POST['employer']
    benefit = request.session['benefit'];

    model = MODEL_MAP[benefit]
    form = get_class(model.__name__+'Form') 

    instance = get_object_or_404(model, id=instance_id)
    form = form(request.POST or None, instance=instance)

    is_valid = form.is_valid()
    if is_valid:
        form.save()

    benefit = request.session['benefit'];
    template = 'account_detail/form/{}.html'.format(benefit.lower())
    body = render(request, template, { 
                                        'form': form, 
                                        'id': instance.id,
                                        'bc': BOOLEAN_CHOICES,
                                        'dtc': DEN_TYPE_CHOICES,
                                        'mtc': MED_TYPE_CHOICES,
                                        'mbc': MED_BOOL_CHOICES,
                                        'ltc': LIFE_TYPE_CHOICES,
                                        'ccc': COSTSHARE_CHOICES,
                                        'sbc': STRATEGY_BOOLEAN_CHOICES
                                    })    

    return JsonResponse({ 'body': body.content, 'is_valid': is_valid }, safe=False)

@login_required(login_url='/login')
def benchmarking(request, benefit):
    request.session['bnchmrk_benefit'] = benefit.upper()

    return render(request, 'benchmarking/benefit.html', {
        'industries': get_industries(),
        'num_employers': 100,
        'EMPLOYER_THRESHOLD': settings.EMPLOYER_THRESHOLD,
        'STATES': STATE_CHOICES
    })


@csrf_exempt
def ajax_benchmarking(request):
    form_param = request.POST
    bnchmrk_benefit = form_param.get('bnchmrk_benefit')
    plan_type = form_param.get('plan_type')

    ft_industries = form_param.getlist('industry[]', ['*'])
    ft_head_counts = form_param.getlist('head_counts[]') or ['0-2000000']
    ft_other = form_param.getlist('others[]')
    ft_regions = form_param.getlist('regions[]')
    ft_states = form_param.getlist('states[]')

    ft_industries_label = form_param.getlist('industry_label[]')
    ft_head_counts_label = form_param.getlist('head_counts_label[]')
    ft_other_label = form_param.getlist('others_label[]')
    ft_regions_label = form_param.getlist('regions_label[]')
    ft_states_label = form_param.getlist('states_label[]')

    request.session['bnchmrk_benefit'] = bnchmrk_benefit
    request.session['plan_type'] = plan_type

    # store for print
    request.session['ft_industries'] = ft_industries
    request.session['ft_head_counts'] = ft_head_counts
    request.session['ft_other'] = ft_other
    request.session['ft_regions'] = ft_regions
    request.session['ft_states'] = ft_states

    request.session['ft_industries_label'] = ft_industries_label
    request.session['ft_head_counts_label'] = ft_head_counts_label
    request.session['ft_other_label'] = ft_other_label
    request.session['ft_regions_label'] = ft_regions_label
    request.session['ft_states_label'] = ft_states_label

    return get_response_template(request, bnchmrk_benefit)


def get_response_template(request, 
                          benefit, 
                          is_print=False, 
                          is_print_header=False):

    today = datetime.strftime(datetime.now(), '%B %d, %Y')
    employers, num_companies = get_filtered_employers_session(request)

    if num_companies < settings.EMPLOYER_THRESHOLD:
        context =  {
            'EMPLOYER_THRESHOLD_MESSAGE': settings.EMPLOYER_THRESHOLD_MESSAGE,
            'num_employers': num_companies,
            'EMPLOYER_THRESHOLD': settings.EMPLOYER_THRESHOLD
        }
    else:
        plan_type = request.session.get('plan_type')
        func_name = 'get_{}_plan'.format(benefit.lower())
        context = globals()[func_name](request, employers, num_companies, plan_type)

    context['base_template'] = 'print/print_body.html' if is_print else 'empty.html'
    context['today'] = today

    template = 'benchmarking/{}.html'.format(benefit.lower())
    if is_print_header:
        template = 'print/print_header.html'

    if is_print:
        # unescape html characters
        h = HTMLParser.HTMLParser()
        context['ft_industries_label'] = h.unescape(', '.join(request.session.get('ft_industries_label', ['All'])))
        context['ft_head_counts_label'] = h.unescape(', '.join(request.session.get('ft_head_counts_label', ['All'])))
        context['ft_other_label'] = h.unescape(', '.join(request.session.get('ft_other_label', ['All'])))
        context['ft_regions_label'] = h.unescape(', '.join(request.session.get('ft_regions_label', ['All'])))
        context['ft_states_label'] = h.unescape(', '.join(request.session.get('ft_states_label', ['All'])))
        context['plan_type'] = plan_type

    return render(request, template, context)


def get_plan_type(request):
    bnchmrk_benefit = request.GET['bnchmrk_benefit'];
    if bnchmrk_benefit == 'MEDICALRX':
        return JsonResponse(['PPO', 'HDHP', 'HMO'], safe=False)
    elif bnchmrk_benefit == 'DENTAL':
        return JsonResponse(['DPPO', 'DMO'], safe=False)
    elif bnchmrk_benefit == 'LIFE':
        return JsonResponse(['Multiple of Salary', 'Flat Amount'], safe=False)
    else:
        return JsonResponse(['All'], safe=False)


def print_report(request):
    return render(request, 'admin/print_report.html', {
        'industries': get_industries(),
        'STATES': STATE_CHOICES
    })    


def print_plan_order(request, company_id):
    plans = []
    for model in [Medical, Dental, Vision, Life, STD, LTD, Strategy]:
        # plans[model.__name__] = []
        attrs = ATTRIBUTE_MAP[model.__name__.upper()]
        for item in model.objects.filter(employer_id=company_id):
            try:
                plan_type = getattr(item, 'type')
                if plan_type in ['PPO', 'POS']:
                    plan_type = 'PPO'
                elif plan_type in ['HMO', 'EPO']:
                    plan_type = 'HMO'
            except Exception as e:
                plan_type = None

            benefit = model.__name__.upper()
            if model == Strategy:
                title = item.employer.name
            else:
                title = item.title
                if model == Life: 
                    if item.type == 'Flat Amount':
                        attrs = [attrs[1]]
                    else:
                        attrs = [attrs[0]]
                elif model == Medical:
                    benefit = 'MEDICALRX'

            plans.append([title, item.pk, benefit, attrs, plan_type])

    return render(request, 'print/print_plan_order.html', { 
        'plans': plans,
        'company': Employer.objects.get(id=company_id).name
    })