import json
from dataclasses import replace

import httpx
import pytest

from app.services.llm import ChatModelClient, ModelUnavailable, parse_output, usage_values
from app.config import Settings

LISTING={'title':'Ufficio test','description':'Ufficio da ristrutturare.', 'property_type':'office',
         'condition':'to_renovate','price':999999,'url':'https://not-sent.example','is_demo':True}
VALID={'summary':'Ufficio da ristrutturare.','strategies':[{'strategy':'value_add','evidence':'da ristrutturare'}],'caveats':[]}


def ready(settings, **kwargs):
    return replace(settings,ai_url='https://llm.example/v1',ai_model='model-under-test',
                   ai_key='test-only-provider-token', **kwargs)


def response(content=VALID, **extra):
    return {'choices':[{'message':{'content':json.dumps(content)},'finish_reason':'stop'}],**extra}


async def test_provider_contract_sends_only_semantic_fields(settings):
    seen=[]
    def handler(req):
        seen.append(json.loads(req.content))
        assert req.url==httpx.URL('https://llm.example/v1/chat/completions')
        assert req.headers['Authorization']=='Bearer test-only-provider-token'
        return httpx.Response(200,json=response(usage={'prompt_tokens':1000,'completion_tokens':100}))
    s=ready(settings,ai_input_price=.5,ai_output_price=2.1)
    analysis,usage=await ChatModelClient(s,httpx.MockTransport(handler)).classify(LISTING)
    assert analysis['engine']=='llm' and analysis['model']=='model-under-test'
    assert 'price' not in json.loads(seen[0]['messages'][1]['content'])
    assert 'url' not in json.loads(seen[0]['messages'][1]['content'])
    assert seen[0]['response_format']=={'type':'json_object'}
    assert usage['estimated_eur']==.00071 and usage['usage_reported']


@pytest.mark.parametrize('content',['not json','[]','{"summary":null}','{"summary":"x","price":1}',
    '{"summary":"x","strategies":[{"strategy":"conversion","evidence":""}]}','{"summary":NaN}'])
def test_invalid_contract_is_never_guessed(content):
    with pytest.raises(ModelUnavailable):
        parse_output(content)


def test_fenced_json_accepted():
    assert parse_output('```json\n'+json.dumps(VALID)+'\n```')['summary']==VALID['summary']


async def test_unsupported_evidence_rejected(settings):
    raw={**VALID,'strategies':[{'strategy':'conversion','evidence':'permesso garantito per appartamenti'}]}
    with pytest.raises(ModelUnavailable,match='citazioni'):
        await ChatModelClient(ready(settings),httpx.MockTransport(lambda _:httpx.Response(200,json=response(raw)))).classify(LISTING)


@pytest.mark.parametrize('status',[401,403,404,302])
async def test_errors_sanitized_and_no_provider_fallback(settings,status):
    calls=[]
    def handler(req):
        calls.append(req)
        return httpx.Response(status,text='sensitive upstream body test-only-provider-token')
    with pytest.raises(ModelUnavailable) as error:
        await ChatModelClient(ready(settings),httpx.MockTransport(handler)).classify(LISTING)
    assert 'sensitive' not in str(error.value) and 'test-only-provider-token' not in str(error.value)
    assert len(calls)==1


async def test_one_rate_limit_retry(settings):
    calls=[]
    def handler(req):
        calls.append(req)
        return httpx.Response(429,headers={'Retry-After':'0'}) if len(calls)==1 else httpx.Response(200,json=response())
    await ChatModelClient(ready(settings),httpx.MockTransport(handler)).classify(LISTING)
    assert len(calls)==2


async def test_long_retry_returns_control_to_scheduler(settings):
    with pytest.raises(ModelUnavailable,match='successiva'):
        await ChatModelClient(ready(settings),httpx.MockTransport(lambda _:httpx.Response(429,headers={'Retry-After':'600'}))).classify(LISTING)


@pytest.mark.parametrize('change',[{'finish_reason':'length'}, {'message':{'content':'{}','tool_calls':[{'name':'shell'}]}}])
async def test_incomplete_or_tool_call_response_rejected(settings,change):
    raw=response();raw['choices'][0].update(change)
    with pytest.raises(ModelUnavailable):
        await ChatModelClient(ready(settings),httpx.MockTransport(lambda _:httpx.Response(200,json=raw))).classify(LISTING)


async def test_missing_key_never_opens_connection(settings):
    def handler(_):
        pytest.fail('Network call with missing configuration')
    with pytest.raises(ModelUnavailable,match='Configura'):
        await ChatModelClient(settings,httpx.MockTransport(handler)).classify(LISTING)


def test_unknown_usage_is_not_zero(settings):
    assert usage_values({},settings)=={'input_tokens':None,'output_tokens':None,'estimated_eur':None,'usage_reported':False}


@pytest.mark.parametrize('kwargs',[{'ai_url':'http://remote.example/v1'}, {'ai_url':'https://u:p@remote.example'},
    {'ai_url':'https://remote.example/v1?secret=x'}, {'ai_timeout':float('nan')}, {'ai_input_price':-1},
    {'ai_format':'unexpected'}, {'ai_reasoning':'unlimited'}, {'max_ai_listings':0}])
def test_configuration_rejects_invalid_values(settings,kwargs):
    with pytest.raises(ValueError):
        replace(settings,**kwargs)


@pytest.mark.parametrize('tools',[
    ['mcp_vedra_get_tasks','mcp_vedra_submit_analysis','mcp_vedra_finish_run','terminal'],
    ['mcp_vedra_get_tasks'], []])
async def test_hermes_refuses_extra_or_missing_tools(settings,tools):
    from app.services.hermes import HermesClient,HermesUnavailable
    with pytest.raises(HermesUnavailable):
        await HermesClient(settings,httpx.MockTransport(lambda _:httpx.Response(200,json=[{'enabled':True,'tools':tools}]))).verify_tools()
