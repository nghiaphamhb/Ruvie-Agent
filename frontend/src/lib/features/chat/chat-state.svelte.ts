import {message} from '../../i18n/messages.ts';
import {ChatApiError,streamChat} from './chat-api.ts';
import type {ChatTurn} from './chat-turn.ts';
import type {ModelsResult} from '../llm/llm-api.ts';

/** One workspace owns these turns and requests; disposal prevents account leakage. */
export function createChatState(options:{onexpired:()=>void;getCatalog:()=>ModelsResult|null;isLocked:()=>boolean;onModelUnavailable:()=>void;onMissingModel?:()=>void}) {
  let draft=$state(''), turns=$state<ChatTurn[]>([]), busy=$state(false);
  let sequence=0, nextId=1, disposed=false, request:AbortController|null=null;
  let activeTurn:ChatTurn|null=null;
  async function send(turn:ChatTurn,modelId:string) {
    const current=++sequence; const controller=new AbortController();
    request=controller;activeTurn=turn;busy=true;
    turn.answer='';turn.citations=[];turn.error=null;turn.status='loading';turn.modelId=modelId;
    const owns=()=>!disposed&&current===sequence;
    let invalidModel=false;
    try {
      await streamChat(turn.question,event=>{
        if(!owns())return;
        if(event.type==='delta'){turn.answer+=event.text;turn.status='streaming';}
        else if(event.type==='citations')turn.citations=event.citations;
        else turn.status='completed';
      },controller.signal,modelId);
    } catch(error) {
      if(!owns())return;
      if(error instanceof ChatApiError&&error.code==='auth_required'){options.onexpired();return;}
      invalidModel=error instanceof ChatApiError&&error.code==='model_unavailable';
      turn.status='error';turn.citations=[];
      turn.error=error instanceof ChatApiError?error.uiMessage:message('chat.errors.complete');
    } finally {
      if(owns()){
        request=null;activeTurn=null;busy=false;
        if(invalidModel)options.onModelUnavailable();
      }
    }
  }
  async function submit(event?:SubmitEvent){
    event?.preventDefault();
    const catalog=options.getCatalog(),question=draft.trim();
    if(disposed||busy||options.isLocked()||!question)return;
    if(!catalog||catalog.selection_required){options.onMissingModel?.();return;}
    const modelId=catalog.selected_model_id;
    if(!modelId||!catalog.models.some(model=>model.id===modelId)){options.onMissingModel?.();return;}
    turns.push({id:nextId++,question,modelId,answer:'',citations:[],status:'loading',error:null});
    draft='';await send(turns[turns.length-1],modelId);
  }
  /** Stop browser output, retain partial text and invalidate even late completed events. */
  function stop(){
    if(!busy)return;
    ++sequence;request?.abort();request=null;busy=false;
    if(activeTurn){activeTurn.status='stopped';activeTurn.citations=[];activeTurn.error=null;}
    activeTurn=null;
  }
  async function retry(id:number,replacementModelId?:string){
    if(disposed||busy||options.isLocked())return;
    const turn=turns.find(item=>item.id===id),catalog=options.getCatalog();
    if(!turn||!catalog||catalog.selection_required)return;
    const modelId=replacementModelId??turn.modelId;
    if(!modelId||!catalog.models.some(model=>model.id===modelId)){
      turn.error=message('chat.retryModel');return;
    }
    // A replacement is explicit and must match the backend-confirmed selection.
    if(replacementModelId&&replacementModelId!==catalog.selected_model_id)return;
    await send(turn,modelId);
  }
  function reset(){stop();++sequence;turns=[];draft='';}
  function dispose(){disposed=true;reset();}
  return {get draft(){return draft;},set draft(value:string){draft=value;},get turns(){return turns;},get busy(){return busy;},submit,stop,retry,reset,dispose};
}
