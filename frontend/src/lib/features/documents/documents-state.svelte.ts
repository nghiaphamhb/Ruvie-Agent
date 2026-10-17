import {message,type MessageKey} from '../../i18n/messages.ts';
import {DocumentsApiError,listProjects,uploadDocument,getRevisionStatus,retrieveDocuments} from './documents-api.ts';
import type {ProjectSummary,RevisionStatus,RetrievalResult} from './documents-api.ts';

/** Upload and search survive view changes but never outlive their login workspace. */
export function createDocumentsState({csrfToken,onexpired}:{csrfToken:string;onexpired:()=>void}) {
  let state=$state({
    projects:[] as ProjectSummary[],projectsLoading:false,projectsError:null as ReturnType<typeof message>|null,
    selectedProjectId:'',uploadTitle:'',uploadSoftware:'',uploadSoftwareVersion:'',selectedFile:null as File|null,
    uploadBusy:false,uploadError:null as ReturnType<typeof message>|null,uploadStatus:null as RevisionStatus|null,
    uploadTimedOut:false,statusRefreshing:false,query:'',results:[] as RetrievalResult[],searchLoading:false,
    searchError:null as ReturnType<typeof message>|null,searched:false
  });
  let disposed=false,uploadSequence=0,searchSequence=0;
  let searchRequest:AbortController|null=null,timer:ReturnType<typeof setTimeout>|null=null,wake:(()=>void)|null=null;
  function wait(){
    return new Promise<void>(resolve=>{wake=resolve;timer=setTimeout(()=>{timer=null;wake=null;resolve();},2000);});
  }
  function fail(error:unknown,key:MessageKey){
    if(error instanceof DocumentsApiError&&error.status===401){onexpired();return null;}
    return message(error instanceof DocumentsApiError&&error.status===404?'upload.errors.notFound':key);
  }
  async function loadProjects(){
    if(disposed||state.projectsLoading)return;
    state.projectsLoading=true;state.projectsError=null;
    try{const result=await listProjects();if(!disposed)state.projects=result;}
    catch(error){if(!disposed)state.projectsError=fail(error,'upload.errors.projects');}
    finally{if(!disposed)state.projectsLoading=false;}
  }
  async function submitUpload(event?:SubmitEvent){
    event?.preventDefault();
    if(disposed||state.uploadBusy||state.statusRefreshing||!state.selectedFile||!state.projects.some(p=>p.id===state.selectedProjectId))return;
    if(state.selectedFile.size>25*1024*1024){state.uploadError=message('upload.tooLarge');return;}
    state.uploadBusy=true;state.uploadError=null;state.uploadStatus=null;state.uploadTimedOut=false;
    const current=++uploadSequence,owns=()=>!disposed&&current===uploadSequence;
    try {
      const result=await uploadDocument(csrfToken,{project_id:state.selectedProjectId,title:state.uploadTitle,software:state.uploadSoftware,software_version:state.uploadSoftwareVersion,file:state.selectedFile});
      if(!owns())return;
      state.uploadStatus={revision_id:result.revision_id,status:result.status,error_code:null};
      const deadline=Date.now()+5*60*1000;
      while(owns()&&Date.now()<deadline){
        await wait();if(!owns()||Date.now()>=deadline)break;
        const status=await getRevisionStatus(result.revision_id);if(!owns())return;
        state.uploadStatus=status;if(status.status==='ready'||status.status==='failed')return;
      }
      if(owns())state.uploadTimedOut=true;
    } catch(error){if(owns())state.uploadError=fail(error,'upload.errors.upload');}
    finally{if(owns())state.uploadBusy=false;}
  }
  async function refreshUploadStatus(){
    if(disposed||!state.uploadStatus||state.uploadBusy||state.statusRefreshing)return;
    const current=uploadSequence;state.statusRefreshing=true;state.uploadError=null;
    try{const result=await getRevisionStatus(state.uploadStatus.revision_id);if(!disposed&&current===uploadSequence)state.uploadStatus=result;}
    catch(error){if(!disposed&&current===uploadSequence)state.uploadError=fail(error,'upload.errors.refresh');}
    finally{if(!disposed&&current===uploadSequence)state.statusRefreshing=false;}
  }
  async function search(){
    const query=state.query.trim();if(disposed||!query)return;
    const current=++searchSequence;searchRequest?.abort();searchRequest=new AbortController();
    state.searchLoading=true;state.searchError=null;state.results=[];state.searched=true;
    try{const result=await retrieveDocuments(query,searchRequest.signal);if(!disposed&&current===searchSequence&&query===state.query.trim())state.results=result;}
    catch(error){if(!disposed&&current===searchSequence&&query===state.query.trim())state.searchError=fail(error,'search.error');}
    finally{if(!disposed&&current===searchSequence){state.searchLoading=false;searchRequest=null;if(query!==state.query.trim())state.searched=false;}}
  }
  function dispose(){
    disposed=true;++uploadSequence;++searchSequence;searchRequest?.abort();if(timer)clearTimeout(timer);wake?.();
    state.selectedFile=null;state.results=[];state.query='';state.projects=[];state.uploadStatus=null;
  }
  // The proxy is session-local; methods only act on this proxy and its request guards.
  return Object.assign(state,{loadProjects,submitUpload,refreshUploadStatus,search,dispose});
}
