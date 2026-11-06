"""Direct Responses API; secrets stay in memory, no Codex dependency."""
import json, os, re, time, threading, urllib.request, urllib.error, http.client
from urllib.parse import urlsplit
from pathlib import Path

ENDPOINT = 'https://api.openai.com/v1/responses'
# The workflow uses one process per stage. Display-only translations may use
# threads; reserve and settle each call atomically within that process.
BUDGET_LOCK = threading.RLock()

class OutputTruncatedError(ValueError):
    pass

def parse_generated_response(raw,config,format_audit=None):
    if (raw.get('incomplete_details') or {}).get('reason')=='max_output_tokens':
        raise OutputTruncatedError('Provider reported output token exhaustion; incomplete output is not accepted.')
    try:
        return parse_response(raw,format_audit)
    except json.JSONDecodeError as error:
        used=(raw.get('usage') or {}).get('output_tokens') or 0
        if used>=config['max_output_tokens']:
            raise OutputTruncatedError('Output reached token limit without a valid complete response; split the stage or increase its output budget.') from error
        raise

def reserve_call(ledger_path,base,name,reserve,config):
    from agent_common import load,save,now
    with BUDGET_LOCK:
        ledger=load(ledger_path) if ledger_path.exists() else dict(reservations=[])
        committed=sum(reserved_charge(x) for x in ledger['reservations'])
        if config.get('run_budget_usd') is not None and committed+reserve>config['run_budget_usd']:
            raise RuntimeError('Budget guard: request not sent. Estimate USD %.4f; remaining %.4f.'%(reserve,config['run_budget_usd']-committed))
        call_limit=config.get('max_calls_per_run',40)
        if call_limit is not None and len(ledger['reservations'])>=call_limit:
            raise RuntimeError('Call-count guard: request not sent.')
        base.mkdir(parents=True,exist_ok=False)
        ledger['reservations'].append(dict(name=name,call_directory=str(base),reserved_usd=reserve,started_at=now()))
        save(ledger_path,ledger)

def settle_call(ledger_path,base,estimate):
    from agent_common import load,save
    with BUDGET_LOCK:
        ledger=load(ledger_path)
        matches=[x for x in ledger['reservations'] if x.get('call_directory')==str(base)]
        if len(matches)!=1:raise ValueError('Ambiguous call reservation')
        matches[0]['settled_estimated_usd']=estimate
        save(ledger_path,ledger)

def api_endpoint(config, route='responses'):
    base=config.get('base_url','https://api.openai.com/v1').rstrip('/')
    parsed=urlsplit(base)
    if (parsed.scheme!='https' or parsed.hostname not in {'api.openai.com','api.tiantoken.com','superai05.com'}
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path!='/v1' or parsed.port not in (None,443)):
        raise RuntimeError('Invalid/unapproved API base URL; no credential sent.')
    if route not in ('responses','models'):
        raise RuntimeError('Unsupported API route')
    return base+'/'+route

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url,code,'Redirect blocked',headers,fp)

def api_opener(config=None):
    config=config or {}
    proxy=os.environ.get('HE_API_PROXY') or os.environ.get('HE_CODEX_PROXY')
    handlers=[NoRedirect()]
    if config.get('connect_timeout_seconds'):
        connect_timeout=config['connect_timeout_seconds']
        read_timeout=config.get('timeout_seconds',600)
        class TimedConnection(http.client.HTTPSConnection):
            def connect(self):
                self.timeout=connect_timeout
                super().connect()
                self.sock.settimeout(read_timeout)
        class TimedHandler(urllib.request.HTTPSHandler):
            def https_open(self,req):
                return self.do_open(TimedConnection,req,context=self._context)
        handlers.append(TimedHandler())
    if proxy:handlers.append(urllib.request.ProxyHandler({'http':proxy,'https':proxy}))
    return urllib.request.build_opener(*handlers)

def get_api_key():
    key = os.environ.get('OPENAI_API_KEY', '').strip()
    if not key:
        raise RuntimeError('OPENAI_API_KEY is not configured; no request sent.')
    return key

def parse_response(raw, format_audit=None):
    if raw.get('status') != 'completed':
        raise ValueError('Response not completed: '+str(raw.get('status')))
    messages=[]
    for item in raw.get('output', []):
        if item.get('type') not in ('message', 'reasoning'):
            raise ValueError('Unexpected tool/output type: '+str(item.get('type')))
        if item.get('type') == 'message':
            messages.append(item)
    finals=[m for m in messages if m.get('phase')=='final_answer']
    if finals:
        if len(finals)!=1:raise ValueError('Ambiguous multiple final responses')
        messages=finals
    elif len(messages)!=1 or messages[0].get('phase') not in (None,'final_answer'):
        raise ValueError('No unambiguous final message')
    chunks=[]
    for item in messages:
        if item.get('status') not in (None,'completed'):raise ValueError('Selected final message not completed')
        if item.get('type') == 'message':
            for content in item.get('content', []):
                if content.get('type') == 'refusal':
                    raise ValueError('Model refused; response preserved, no automatic retry.')
                if content.get('type') == 'output_text':
                    chunks.append(content['text'])
    text=''.join(chunks)
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        if error.msg!='Extra data':raise
        value,end=json.JSONDecoder().raw_decode(text.lstrip())
        suffix=text.lstrip()[end:]
        if not isinstance(value,dict) or not re.fullmatch(r'[\]}\s]{1,16}',suffix):raise
        if format_audit is not None:
            format_audit.append(dict(operation='Ignore redundant closing delimiters after one complete JSON object',suffix=suffix,scientific_fields_changed=False))
        return value


def read_response_stream(response, base):
    """Read Responses SSE; partial deltas never count as a completed answer.

    Official format: https://developers.openai.com/api/docs/guides/streaming-responses
    Streaming compatibility of a third-party endpoint must be verified at runtime.
    """
    from agent_common import save, now
    base=Path(base);data=[];events=0;characters=0;last_saved=0
    with (base/'stream_events.jsonl').open('x',encoding='utf-8') as log:
        for raw_line in response:
            line=raw_line.decode('utf-8').rstrip('\r\n')
            if len(line)>4_000_000:raise ValueError('Oversized SSE line')
            if line.startswith('data:'):
                data.append(line[5:].lstrip(' '));continue
            if line or not data:continue
            body='\n'.join(data);data=[]
            if body=='[DONE]':break
            event=json.loads(body);kind=event.get('type');events+=1
            if kind=='error':
                # Service error text can echo request credentials; never save it.
                log.write(json.dumps({'type':'error','message':'Provider SSE error; raw body omitted'})+'\n');log.flush()
                raise ValueError('Provider reported SSE error')
            safe_event=({'type':kind,'metadata_omitted':True} if kind=='codex.response.metadata' else event)
            log.write(json.dumps(safe_event,ensure_ascii=False)+'\n');log.flush()
            if kind=='response.output_text.delta':characters+=len(event.get('delta',''))
            terminal=kind in ('response.completed','response.incomplete','response.failed')
            if time.monotonic()-last_saved>10 or terminal:
                save(base/'stream_progress.json',dict(updated_at=now(),events=events,output_characters=characters,last_event=kind,terminal=terminal))
                last_saved=time.monotonic()
            if terminal:
                if not isinstance(event.get('response'),dict):raise ValueError('Terminal SSE event missing response')
                return event['response']
        raise ValueError('SSE ended without terminal response; partial output is not accepted')

def estimate_charge(input_tokens, output_tokens, cached_tokens=0, model='gpt-6.1-sol'):
    """Standard Sol rates checked 2026-10-28; excludes tax and cache writes."""
    long = input_tokens > 272000
    if model=='gpt-5.4':
        return ((input_tokens-cached_tokens)*(5 if long else 2.5)+cached_tokens*(.5 if long else .25)+output_tokens*(22.5 if long else 15))/1_000_000
    if model!='gpt-6.1-sol':raise ValueError('No pricing configured for model')
    return ((input_tokens-cached_tokens)*(4 if long else 2)
            + cached_tokens*(.2 if long else .1)
            + output_tokens*(15 if long else 10))/1_000_000

def reserved_charge(entry):
    return entry.get('settled_estimated_usd',entry['reserved_usd'])

def count_input_estimate(wire):
    # Local tokenizer estimate + 20% and framing allowance; not provider-exact.
    try:
        import tiktoken, math
        return math.ceil(len(tiktoken.get_encoding('o200k_base').encode(wire.decode('utf-8'),disallowed_special=()))*1.2)+2048
    except ImportError:
        return len(wire)+2048

def model_identity(raw, config):
    observed=raw.get('model')
    if observed==config['model']:
        return 'provider_reported_match'
    if config['model']=='gpt-5.4' and observed=='gpt-5.4-2026-03-05':
        return 'provider_reported_documented_snapshot'
    if observed is None and config.get('allow_unreported_model') is True and urlsplit(config.get('base_url','')).hostname=='api.tiantoken.com':
        return 'unverified_provider_omitted_model'
    raise ValueError('Provider model missing or different; response rejected.')


def call_api(run, name, instruction, payload, schema, overrides=None):
    from agent_common import ROOT, BOUNDARY, load, save, sha, now, validate_json, budget_path
    config=load(Path(os.environ.get('AGENT_RUNTIME_CONFIG',str(ROOT/'spec/runtime.json'))))
    config.update(overrides or {})
    config['max_output_tokens']=max(config['max_output_tokens'],config.get('minimum_output_tokens',0))
    if config.get('run_budget_usd') is None and not config.get('unlimited_budget_authorized',False):
        raise RuntimeError('An explicit numeric budget is required for a new paid run.')
    endpoint=api_endpoint(config)
    if not config.get('live_generation_enabled',True):
        raise RuntimeError('Paid generation disabled; no request sent. Read-only model access check remains available.')
    if config.get('model') not in ('gpt-6.1-sol','gpt-5.4','gpt-5.6-terra'):
        raise RuntimeError('Unsupported model; configure model validation before sending requests.')
    key=get_api_key()
    run=Path(run)
    boundary=BOUNDARY
    if config.get('task_kind')=='display_translation':
        boundary=boundary.replace('All scientific output must be in English, except verbatim source quotations.','Translate the frozen English content into Chinese for display only. Do not add, remove, improve, or reassess scientific claims; preserve uncertainty, IDs and numbers.')
    prompt=boundary+instruction+'\nINPUT_JSON\n'+json.dumps(payload,ensure_ascii=False)
    request=dict(model=config['model'],input=prompt,
        text=dict(format=dict(type='json_schema',name='research_output',strict=True,schema=schema)),
        max_output_tokens=config['max_output_tokens'],store=False)
    if config.get('reasoning_effort'):
        request['reasoning']=dict(effort=config['reasoning_effort'])
    if config.get('stream',False):request['stream']=True
    wire=json.dumps(request,ensure_ascii=False).encode('utf-8')
    multiplier=config.get('billing_group_multiplier',1)
    pricing_model=config.get('pricing_reference_model',config['model'])
    input_estimate=count_input_estimate(wire)
    reserve=estimate_charge(input_estimate,config['max_output_tokens'],model=pricing_model)*multiplier
    ledger_path=budget_path(run)
    base=run/'calls'/name
    reserve_call(ledger_path,base,name,reserve,config)
    save(base/'runtime.snapshot.json',config)
    save(base/'input.json',payload);save(base/'schema.json',schema)
    (base/'prompt.txt').write_text(prompt,encoding='utf-8')
    save(base/'request.json',request)
    for source in ROOT.glob('*.py'):
        (base/(source.name+'.snapshot')).write_bytes(source.read_bytes())
    save(base/'invocation.json',dict(started_at=now(),provider=config.get('service_name','openai'),endpoint=endpoint,
        model_requested=config['model'],reasoning_effort=config.get('reasoning_effort'),
        authentication='OPENAI_API_KEY from process or Windows user environment; never saved',
        input_sha256=sha(base/'input.json'),prompt_sha256=sha(base/'prompt.txt'),
        reserved_usd=reserve,automatic_retries=0))
    started=now()
    try:
        req=urllib.request.Request(endpoint,data=wire,headers={
            'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        opener=api_opener(config)
        with opener.open(req,timeout=config['timeout_seconds']) as response:
            request_id=response.headers.get('x-request-id')
            content_type=response.headers.get('Content-Type','')
            save(base/'transport_headers.json',dict(received_at=now(),content_type=content_type,
                requested_stream=bool(config.get('stream')),request_id=request_id))
            raw=read_response_stream(response,base) if 'text/event-stream' in content_type else json.loads(response.read().decode('utf-8'))
        save(base/'api_response.json',raw)
        usage=raw.get('usage') or {}
        input_tokens=usage.get('input_tokens',0);output_tokens=usage.get('output_tokens',0)
        cached=(usage.get('input_tokens_details') or {}).get('cached_tokens',0)
        audit=dict(provider=config.get('service_name','openai'),endpoint=endpoint,tool_events=0,model_requested=config['model'],
            model_observed=raw.get('model'),request_id=request_id,response_id=raw.get('id'),
            usage=[dict(input_tokens=input_tokens,output_tokens=output_tokens,cached_input_tokens=cached,
                reasoning_output_tokens=(usage.get('output_tokens_details') or {}).get('reasoning_tokens',0))],
            api_usage=usage,estimated_usd=estimate_charge(input_tokens,output_tokens,cached,model=pricing_model)*multiplier if usage else None,
            official_rate_reference_usd=estimate_charge(input_tokens,output_tokens,cached,model=pricing_model),
            billing_group_multiplier=multiplier,
            cost_note='Estimated platform dollar credits using configured group multiplier; not invoice; cache writes/tax may differ.')
        save(base/'audit.json',audit)
        if usage:
            settle_call(ledger_path,base,audit['estimated_usd'])
        identity=model_identity(raw,config)
        audit['model_identity_status']=identity
        save(base/'audit.json',audit)
        format_audit=[]
        result=parse_generated_response(raw,config,format_audit)
        validate_json(result,schema)
        if format_audit:save(base/'format_normalization.json',dict(raw_response_sha256=sha(base/'api_response.json'),operations=format_audit,schema_valid=True))
        save(base/'response.json',result)
        save(base/'attempt_1.status.json',dict(started_at=started,completed_at=now(),exit_code=0,error=None))
        save(base/'success.json',dict(completed_at=now(),response_sha256=sha(base/'response.json'),attempt=1,provider=config.get('service_name','openai')))
        print('REAL_API_CALL_COMPLETED '+name,flush=True)
        return result
    except urllib.error.HTTPError as error:
        # Server errors may echo credentials. Save only safe classification, never raw error body.
        status=error.code
        category='unclassified_provider_error'
        retry_after=error.headers.get('Retry-After') if error.headers else None
        retry_after=retry_after if retry_after and retry_after.isdigit() else None
        try:
            body=json.loads(error.read().decode('utf-8'));detail=body.get('error',{})
            code=detail.get('code') if isinstance(detail,dict) else None
            message=str(detail.get('message','') if isinstance(detail,dict) else detail).lower()
            if any(t in message for t in ('insufficient_quota','no balance','\u4f59\u989d\u4e0d\u8db3','quota exceeded','billing quota','credit exhausted')):
                category='quota_or_balance'
            elif any(t in message for t in ('rate limit','too many requests','tokens per min','requests per min','\u9650\u6d41','\u9891\u7387')):
                category='rate_limit'
            elif any(t in message for t in ('upstream','channel','\u6e20\u9053','overload','capacity')):
                category='provider_upstream_or_capacity'
            code=code if isinstance(code,str) and re.fullmatch(r'[a-zA-Z0-9_\-]{1,80}',code) else None
        except Exception:
            code=None
        safe=dict(started_at=started,completed_at=now(),exit_code=1,http_status=status,error_code=code,
            error_category=category,retry_after_seconds=retry_after,
            error='API request rejected; no retry; key and raw error body omitted.')
        save(base/'attempt_1.status.json',safe)
        raise RuntimeError('API HTTP '+str(status)+'; code='+str(code)+'; see saved status.') from None
    except Exception as error:
        import jsonschema
        category=('output_truncated' if isinstance(error,OutputTruncatedError) else
                  'model_json_invalid' if isinstance(error,json.JSONDecodeError) and (base/'api_response.json').exists() else
                  'transport_json_invalid' if isinstance(error,json.JSONDecodeError) else
                  'schema_mismatch' if isinstance(error,jsonschema.ValidationError) else 'request_or_validation_error')
        save(base/'attempt_1.status.json',dict(started_at=started,completed_at=now(),exit_code=1,
            error_type=type(error).__name__,error_category=category,
            error='Request or validation failed; no retry; inspect saved response if present.'))
        parse_error=error.__cause__ if isinstance(error,OutputTruncatedError) else error
        if isinstance(parse_error,json.JSONDecodeError):
            save(base/'parse_diagnostic.json',dict(category=category,line=parse_error.lineno,column=parse_error.colno,position=parse_error.pos,reason=parse_error.msg))
        raise RuntimeError('API '+type(error).__name__+'; no automatic retry; logs at '+str(base)) from None
