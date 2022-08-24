Search.setIndex({docnames:["alab_management","alab_management.config","alab_management.data_explorer","alab_management.device_manager","alab_management.device_view","alab_management.device_view.device","alab_management.device_view.device_view","alab_management.experiment_manager","alab_management.experiment_view","alab_management.experiment_view.experiment","alab_management.experiment_view.experiment_view","alab_management.lab_view","alab_management.logger","alab_management.sample_view","alab_management.sample_view.sample","alab_management.sample_view.sample_view","alab_management.task_actor","alab_management.task_manager","alab_management.task_view","alab_management.task_view.task","alab_management.task_view.task_enums","alab_management.task_view.task_view","alab_management.user_input","development","device_definition","index","installation","modules","setup","task_definition"],envversion:{"sphinx.domains.c":2,"sphinx.domains.changeset":1,"sphinx.domains.citation":1,"sphinx.domains.cpp":5,"sphinx.domains.index":1,"sphinx.domains.javascript":2,"sphinx.domains.math":2,"sphinx.domains.python":3,"sphinx.domains.rst":2,"sphinx.domains.std":2,"sphinx.ext.intersphinx":1,"sphinx.ext.todo":2,"sphinx.ext.viewcode":1,sphinx:56},filenames:["alab_management.rst","alab_management.config.rst","alab_management.data_explorer.rst","alab_management.device_manager.rst","alab_management.device_view.rst","alab_management.device_view.device.rst","alab_management.device_view.device_view.rst","alab_management.experiment_manager.rst","alab_management.experiment_view.rst","alab_management.experiment_view.experiment.rst","alab_management.experiment_view.experiment_view.rst","alab_management.lab_view.rst","alab_management.logger.rst","alab_management.sample_view.rst","alab_management.sample_view.sample.rst","alab_management.sample_view.sample_view.rst","alab_management.task_actor.rst","alab_management.task_manager.rst","alab_management.task_view.rst","alab_management.task_view.task.rst","alab_management.task_view.task_enums.rst","alab_management.task_view.task_view.rst","alab_management.user_input.rst","development.rst","device_definition.rst","index.rst","installation.rst","modules.rst","setup.rst","task_definition.rst"],objects:{"":[[0,0,0,"-","alab_management"]],"alab_management.config":[[1,1,1,"","froze_config"]],"alab_management.device_manager":[[3,2,1,"","DeviceManager"],[3,2,1,"","DeviceMethodCallState"],[3,2,1,"","DeviceWrapper"],[3,2,1,"","DevicesClient"],[3,2,1,"","MethodCallStatus"]],"alab_management.device_manager.DeviceManager":[[3,3,1,"","on_message"],[3,3,1,"","run"]],"alab_management.device_manager.DeviceMethodCallState":[[3,4,1,"","future"],[3,4,1,"","last_updated"],[3,4,1,"","status"]],"alab_management.device_manager.DeviceWrapper":[[3,2,1,"","DeviceMethodWrapper"],[3,5,1,"","name"]],"alab_management.device_manager.DeviceWrapper.DeviceMethodWrapper":[[3,5,1,"","method"]],"alab_management.device_manager.DevicesClient":[[3,3,1,"","call"],[3,3,1,"","create_device_wrapper"],[3,3,1,"","on_message"]],"alab_management.device_manager.MethodCallStatus":[[3,4,1,"","FAILURE"],[3,4,1,"","IN_PROGRESS"],[3,4,1,"","PENDING"],[3,4,1,"","SUCCESS"]],"alab_management.device_view":[[5,0,0,"-","device"],[6,0,0,"-","device_view"]],"alab_management.device_view.device":[[24,2,1,"","BaseDevice"],[5,1,1,"","add_device"],[5,1,1,"","get_all_devices"]],"alab_management.device_view.device.BaseDevice":[[24,3,1,"","__init__"],[5,3,1,"","connect"],[24,4,1,"","description"],[5,3,1,"","disconnect"],[24,3,1,"","emergent_stop"],[5,3,1,"","is_running"],[5,5,1,"","message"],[24,5,1,"","sample_positions"],[5,3,1,"","set_message"]],"alab_management.device_view.device_view":[[6,6,1,"","DeviceConnectionError"],[6,2,1,"","DeviceStatus"],[6,2,1,"","DeviceView"]],"alab_management.device_view.device_view.DeviceStatus":[[6,4,1,"","ERROR"],[6,4,1,"","HOLD"],[6,4,1,"","IDLE"],[6,4,1,"","OCCUPIED"],[6,4,1,"","UNKNOWN"]],"alab_management.device_view.device_view.DeviceView":[[6,3,1,"","add_devices_to_db"],[6,3,1,"","execute_command"],[6,3,1,"","get_all"],[6,3,1,"","get_available_devices"],[6,3,1,"","get_device"],[6,3,1,"","get_devices_by_task"],[6,3,1,"","get_samples_on_device"],[6,3,1,"","get_status"],[6,3,1,"","occupy_device"],[6,3,1,"","query_property"],[6,3,1,"","release_device"],[6,3,1,"","request_devices"],[6,3,1,"","set_message"],[6,3,1,"","sync_device_status"]],"alab_management.experiment_manager":[[7,2,1,"","ExperimentManager"]],"alab_management.experiment_manager.ExperimentManager":[[7,3,1,"","handle_pending_experiments"],[7,3,1,"","mark_completed_experiments"],[7,3,1,"","run"]],"alab_management.experiment_view":[[9,0,0,"-","experiment"],[10,0,0,"-","experiment_view"]],"alab_management.experiment_view.experiment":[[9,2,1,"","InputExperiment"]],"alab_management.experiment_view.experiment.InputExperiment":[[9,4,1,"","name"],[9,4,1,"","samples"],[9,4,1,"","tasks"]],"alab_management.experiment_view.experiment_view":[[10,2,1,"","ExperimentStatus"],[10,2,1,"","ExperimentView"]],"alab_management.experiment_view.experiment_view.ExperimentStatus":[[10,4,1,"","COMPLETED"],[10,4,1,"","ERROR"],[10,4,1,"","PENDING"],[10,4,1,"","RUNNING"]],"alab_management.experiment_view.experiment_view.ExperimentView":[[10,3,1,"","create_experiment"],[10,3,1,"","get_experiment"],[10,3,1,"","get_experiment_by_sample_id"],[10,3,1,"","get_experiment_by_task_id"],[10,3,1,"","get_experiments_with_status"],[10,3,1,"","update_experiment_status"],[10,3,1,"","update_sample_task_id"]],"alab_management.logger":[[12,2,1,"","DBLogger"],[12,2,1,"","LoggingLevel"],[12,2,1,"","LoggingType"]],"alab_management.logger.DBLogger":[[12,3,1,"","filter_log"],[12,3,1,"","log"],[12,3,1,"","log_amount"],[12,3,1,"","log_characterization_result"],[12,3,1,"","log_device_signal"],[12,3,1,"","system_log"]],"alab_management.logger.LoggingLevel":[[12,4,1,"","CRITICAL"],[12,4,1,"","DEBUG"],[12,4,1,"","ERROR"],[12,4,1,"","FATAL"],[12,4,1,"","INFO"],[12,4,1,"","WARN"],[12,4,1,"","WARNING"]],"alab_management.logger.LoggingType":[[12,4,1,"","CHARACTERIZATION_RESULT"],[12,4,1,"","DEVICE_SIGNAL"],[12,4,1,"","OTHER"],[12,4,1,"","SAMPLE_AMOUNT"],[12,4,1,"","SYSTEM_LOG"]],"alab_management.sample_view":[[14,0,0,"-","sample"],[15,0,0,"-","sample_view"]],"alab_management.sample_view.sample":[[14,2,1,"","Sample"],[14,2,1,"","SamplePosition"],[14,1,1,"","add_standalone_sample_position"],[14,1,1,"","get_all_standalone_sample_positions"]],"alab_management.sample_view.sample.Sample":[[14,4,1,"","name"],[14,4,1,"","position"],[14,4,1,"","sample_id"],[14,4,1,"","task_id"]],"alab_management.sample_view.sample.SamplePosition":[[14,4,1,"","SEPARATOR"],[14,4,1,"","description"],[14,4,1,"","name"],[14,4,1,"","number"]],"alab_management.sample_view.sample_view":[[15,2,1,"","SamplePositionRequest"],[15,2,1,"","SamplePositionStatus"],[15,2,1,"","SampleView"]],"alab_management.sample_view.sample_view.SamplePositionRequest":[[15,2,1,"","Config"],[15,3,1,"","from_py_type"],[15,3,1,"","from_str"],[15,4,1,"","number"],[15,4,1,"","prefix"]],"alab_management.sample_view.sample_view.SamplePositionRequest.Config":[[15,4,1,"","extra"]],"alab_management.sample_view.sample_view.SamplePositionStatus":[[15,4,1,"","EMPTY"],[15,4,1,"","LOCKED"],[15,4,1,"","OCCUPIED"]],"alab_management.sample_view.sample_view.SampleView":[[15,3,1,"","add_sample_positions_to_db"],[15,3,1,"","clean_up_sample_position_collection"],[15,3,1,"","create_sample"],[15,3,1,"","get_available_sample_position"],[15,3,1,"","get_sample"],[15,3,1,"","get_sample_position"],[15,3,1,"","get_sample_position_parent_device"],[15,3,1,"","get_sample_position_status"],[15,3,1,"","get_sample_positions_by_task"],[15,3,1,"","is_unoccupied_position"],[15,3,1,"","lock_sample_position"],[15,3,1,"","move_sample"],[15,3,1,"","release_sample_position"],[15,3,1,"","request_sample_positions"],[15,3,1,"","update_sample_task_id"]],"alab_management.task_actor":[[16,6,1,"","ParameterError"]],"alab_management.task_view":[[19,0,0,"-","task"],[20,0,0,"-","task_enums"],[21,0,0,"-","task_view"]],"alab_management.task_view.task":[[29,2,1,"","BaseTask"],[19,1,1,"","add_reroute_task"],[19,1,1,"","add_task"],[19,1,1,"","get_all_tasks"]],"alab_management.task_view.task.BaseTask":[[29,3,1,"","__init__"],[19,5,1,"","priority"],[29,3,1,"","run"],[19,3,1,"","run_subtask"]],"alab_management.task_view.task_enums":[[20,2,1,"","TaskPriority"],[20,2,1,"","TaskStatus"]],"alab_management.task_view.task_enums.TaskPriority":[[20,4,1,"","HIGH"],[20,4,1,"","LOW"],[20,4,1,"","NORMAL"],[20,4,1,"","URGENT"]],"alab_management.task_view.task_enums.TaskStatus":[[20,4,1,"","COMPLETED"],[20,4,1,"","ERROR"],[20,4,1,"","INITIATED"],[20,4,1,"","PAUSED"],[20,4,1,"","READY"],[20,4,1,"","REQUESTING_RESOURCES"],[20,4,1,"","RUNNING"],[20,4,1,"","STOPPED"],[20,4,1,"","WAITING"]],"alab_management.task_view.task_view":[[21,2,1,"","TaskView"]],"alab_management.task_view.task_view.TaskView":[[21,3,1,"","create_subtask"],[21,3,1,"","create_task"],[21,3,1,"","encode_task"],[21,3,1,"","get_ready_tasks"],[21,3,1,"","get_status"],[21,3,1,"","get_task"],[21,3,1,"","get_task_with_sample"],[21,3,1,"","get_tasks_by_status"],[21,3,1,"","try_to_mark_task_ready"],[21,3,1,"","update_result"],[21,3,1,"","update_status"],[21,3,1,"","update_subtask_result"],[21,3,1,"","update_subtask_status"],[21,3,1,"","update_task_dependency"]],"alab_management.user_input":[[22,2,1,"","UserInputView"],[22,2,1,"","UserRequestStatus"],[22,1,1,"","request_user_input"]],"alab_management.user_input.UserInputView":[[22,3,1,"","clean_up_user_input_collection"],[22,3,1,"","get_all_pending_requests"],[22,3,1,"","get_request"],[22,3,1,"","insert_request"],[22,3,1,"","retrieve_user_input"],[22,3,1,"","update_request_status"]],"alab_management.user_input.UserRequestStatus":[[22,4,1,"","ERROR"],[22,4,1,"","FULLFILLED"],[22,4,1,"","PENDING"]],alab_management:[[1,0,0,"-","config"],[2,0,0,"-","data_explorer"],[3,0,0,"-","device_manager"],[4,0,0,"-","device_view"],[7,0,0,"-","experiment_manager"],[8,0,0,"-","experiment_view"],[12,0,0,"-","logger"],[13,0,0,"-","sample_view"],[16,0,0,"-","task_actor"],[18,0,0,"-","task_view"],[22,0,0,"-","user_input"]]},objnames:{"0":["py","module","Python module"],"1":["py","function","Python function"],"2":["py","class","Python class"],"3":["py","method","Python method"],"4":["py","attribute","Python attribute"],"5":["py","property","Python property"],"6":["py","exception","Python exception"]},objtypes:{"0":"py:module","1":"py:function","2":"py:class","3":"py:method","4":"py:attribute","5":"py:property","6":"py:exception"},terms:{"0":[19,29],"1":[3,6,10,12,14,15,20],"10":[12,20],"100":20,"1d":12,"1h":12,"2":[3,6,10,12,15,20],"20":[12,20],"27017":[1,28],"3":[3,6,10,12,15,20],"30":[12,20],"3c79e5035567c8ef3267":23,"4":[3,6,10,12,19,20,29],"40":12,"5":[6,12,20],"50":12,"502":24,"5672":1,"6":20,"7":20,"8":20,"9":20,"abstract":[5,19,24,25,29],"case":5,"class":[3,5,6,7,9,10,12,14,15,19,20,21,22,24,25,29],"default":[15,28],"do":25,"enum":[3,6,10,12,15,20,22],"float":[3,29],"function":[3,6,12,15,16,19,24,25,29],"import":25,"int":[12,14,19,24],"long":15,"new":[15,21],"return":[1,3,5,6,10,12,14,15,19,21,22,24,29],"super":[24,29],"true":[3,6,22],"try":[15,19,21,29],"while":[19,29],A:[3,10,12,14,15,25,28],At:10,By:15,For:[24,25,28],If:[6,15,21,28],In:[19,25,29],It:[1,5,7,16,21,24,25],The:[3,5,6,10,14,15,16,19,20,24,25,28,29],There:6,To:[23,24,26,28],With:25,_:15,__exit__:[6,15],__init__:[24,28,29],_a:15,_base:3,_bodi:3,_check_statu:3,_id:21,_sampl:9,_task:9,abc:[5,19],about:[5,19,24,29],access:[3,5,26],accord:28,across:15,action:23,actor:20,actual:15,acycl:25,adapt:3,add:[10,21,23],add_devic:5,add_devices_to_db:6,add_reroute_task:19,add_sample_positions_to_db:15,add_standalone_sample_posit:14,add_task:19,addit:5,address:24,administ:3,aim:25,alab:[7,25,28],alab_manag:[23,24,26],alabo:[5,28],all:[1,3,5,6,14,15,19,21,22,24,25,29],alloc:[19,29],allow:[1,25],alreadi:[6,15],also:[10,19,21,23,25,28,29],amount:12,an:[1,3,5,10,19,24,25,29],ani:[3,5,6,7,10,12,15,21,22,24],apart:23,api:6,appear:[6,15],appropri:5,ar:[5,7,15,19,20,21,24,25,29],architectur:25,arg:[3,5,6,19,24,29],argument:3,assign:[10,19,21,25,28,29],attribut:[5,24],attributeerror:6,authent:28,automat:[19,28,29],autonom:[0,25],avail:[15,19,29],back:3,base:[3,5,6,7,9,10,12,14,15,16,19,20,21,22],basedevic:[5,6,24,25],basemodel:[9,15],basetask:[19,21,25,29],basic:[3,12,14,25],batch:25,batteri:12,becaus:5,been:[10,14,20],befor:[21,23,28],besid:28,between:25,block:22,bool:[5,6,15,21,22],both:15,briefli:14,bson:14,call:[3,5,6,15,16,19,29],callabl:6,callback:3,can:[3,5,12,14,15,19,21,23,24,25,28,29],cannot:[19,20,21,29],cd:[23,26],cedergrouphub:[23,26],certain:[3,12,25],chang:23,channel:3,character:12,characterization_result:12,charg:12,check:[5,15,21,23],chemic:[12,25],classmethod:15,classvar:[5,14,24],clean_up_sample_position_collect:15,clean_up_user_input_collect:22,client:3,clone:[23,26],code:[23,24,25],collect:[6,7,10,15,21,22,25],com:[3,23,26],come:[12,26],command:[3,19,23,29],commun:[6,23,25],complet:[7,10,19,20,21,22,25,29],concurr:3,conduct:[3,25],config:[0,15,27,28],config_:1,configur:[1,25],conflict:[19,29],connect:[5,6,24,28],connect_to_devic:6,constrainedintvalu:15,constrainedstrvalu:9,construct:25,contain:[1,10,21,25],content:27,context:[19,29],conveni:21,convert:1,convien:21,coordin:[5,14,24],correct:20,correctli:23,correspond:[21,29],creat:[3,10,15,21,25],create_device_wrapp:3,create_experi:10,create_sampl:15,create_subtask:21,create_task:21,creation:10,critic:12,current:[5,14,19,20,21,23,25,29],custom:[12,24,26,28,29],cycl:25,dag:25,dashboard:[5,6,22],data:[1,9,12,15,19,29],data_explor:[0,27],databas:[6,7,9,10,12,14,15,16,19,21,22,25,26,28,29],db:[6,15,28],dblogger:12,debug:12,def:[5,24,29],default_lab:1,defin:[3,5,9,14,15,19,25,28],definit:[6,14,25,26],depend:[23,25],describ:[5,14,24,25],descript:[5,6,14,15,24],dest:[19,29],dev:23,devic:[0,3,4,6,12,14,15,19,25,26,28,29],device_1:28,device_2:28,device_3:28,device_manag:[0,27],device_nam:[3,6],device_names_str:6,device_rpc:3,device_sign:12,device_str:6,device_typ:6,device_type_nam:6,device_type_str:6,device_types_str:6,device_view:[0,27],deviceconnectionerror:6,devicemanag:3,devicemethodcallst:3,devicemethodwrapp:3,devices_and_posit:[19,29],devices_cli:3,devicescli:3,deviceslock:6,devicestatu:6,deviceview:6,devicewrapp:[3,5],dict:[1,3,5,6,10,12,14,15,19,21,22],die:25,differ:12,dir:28,direct:25,directli:3,directori:28,disconnect:5,discuss:26,displai:5,doe:[5,24],doesn:[5,24],done:[7,10,25],dramatiq:[16,25],driver:[3,24,25],drop:[15,22],dump:21,duplic:6,dure:[12,20],e:[12,19,23,25,26,29],each:25,easili:[23,25],els:[12,15],emerg:[5,24],emergent_stop:[5,24],empti:[15,25,28],encod:21,encode_task:21,encount:20,end:25,entri:[6,15,21],enumer:3,ericavonb:23,error:[6,10,12,15,20,22],etc:25,even:[5,15,25],event:7,everi:3,everyth:0,exampl:[1,5,19,24,28,29],except:[6,16],execut:[3,12,20],execute_command:6,executor:7,exist:15,exp_id:10,experi:[0,7,8,10],experiment_manag:[0,27],experiment_view:[0,27],experimentmanag:7,experimentstatu:10,experimentview:10,extens:25,extra:15,f:[5,24],fail:6,failur:3,fals:[6,21,22],fatal:12,feed:3,file:1,filter:10,filter_log:12,find:[7,12],finish:[7,20,21],first:23,five:25,flag:7,flake8:23,flexibl:25,folder:26,follow:[1,9,23,28],forbid:15,format:[9,10,23,25],found:[6,15,21],from:[1,3,5,7,12,19,21,22,23,24,25,29],from_py_typ:15,from_str:15,froze_config:1,frozen:1,frozen_config:1,fulfil:22,fullfil:22,furnac:[5,12,19,24,29],furnace_1:15,furnace_t:[5,24],furnacecontrol:24,futur:3,g:[12,23,25],gener:[1,6,28],geograph:14,get:[1,3,5,6,10,14,15,19,21,22,29],get_al:6,get_all_devic:5,get_all_pending_request:22,get_all_standalone_sample_posit:14,get_all_task:19,get_available_devic:6,get_available_sample_posit:15,get_devic:6,get_devices_by_task:6,get_experi:10,get_experiment_by_sample_id:10,get_experiment_by_task_id:10,get_experiments_with_statu:10,get_ready_task:21,get_request:22,get_sampl:15,get_sample_posit:15,get_sample_position_parent_devic:15,get_sample_position_statu:15,get_sample_positions_by_task:15,get_samples_on_devic:6,get_statu:[6,21],get_task:21,get_task_with_sampl:21,get_tasks_by_statu:21,get_temperatur:[19,29],gist:23,git:[25,26],github:[3,23,25,26],give:22,given:[6,10,15,21,22],global:23,graph:25,great:25,ha:[6,10,14,15,19,20,25,28,29],handl:[3,21,28],handle_pending_experi:7,have:[6,25,26],heat:[5,24,25,29],here:[5,19,23,24,29],high:20,higher:[12,20],highli:23,hold:[3,5,6,14,24,25],host:[1,25,28],how:[5,19,24,26,28,29],http:[3,23],i:[19,29],id:[6,10,14,15,19,21,22,25,29],identifi:[5,6,14,24,29],idl:[6,25],ie:15,implement:25,in_progress:3,includ:[5,6,15,24],incom:7,index:25,indic:[6,15],info:[12,15,21],inform:[5,12,23,24,25],inherit:[5,19,21,24,25,29],init:28,initi:[14,16,20,24],input:22,inputexperi:[9,10],insert:[6,10,15,21,22],insert_request:22,insid:[3,5,19,24,29],inside_furnac:[19,29],instal:23,instanc:[3,5,14,15,25],instanti:25,integ:20,intend:10,intenum:20,interest:21,introduc:28,involvend:29,is_run:[5,19,29],is_unoccupied_posit:15,iter:12,its:[6,10,15,21,25],itself:28,job:21,just:[5,15,25,28],keyword:3,kind:[5,24],kwarg:[3,5,6,15,19,24,29],lab:[0,5,10,14,19,24,28,29],lab_view:[0,19,27,29],labview:[10,29],larger:20,last_upd:3,later:10,launch:[16,25],least:26,level:12,life:25,like:[25,28],list:[3,5,6,9,10,15,21,22,24,25,29],listen:3,load:28,local:26,localhost:[1,28],lock:[15,25],lock_sample_posit:15,log:[12,19,29],log_amount:12,log_characterization_result:12,log_data:12,log_device_sign:[12,19,29],logger:[0,19,27,29],logging_typ:12,logginglevel:12,loggingtyp:12,look:[15,28],loop:7,low:20,m:28,mai:[6,23,25,28],main:[9,15,25],mainten:22,make:[5,23],manag:[0,3,7,10,15,19,21,22,28,29],mani:7,manipul:21,manual:[5,24],map:[5,24],mappingproxi:1,mark:[7,21,22],mark_completed_experi:7,match:15,matter:[5,24],maus:3,messag:[3,5,6,23],method:[3,5,6,7,10,15,21,24],method_fram:3,method_handl:3,methodcallstatu:3,modifi:1,modul:[27,28],mongodb:[1,21,23,25,26],more:[19,23,24,28],move:[19,25,29],move_sampl:15,moving_task:[19,29],multipl:25,must:[5,21,25,26,28],name:[1,3,5,6,9,14,15,19,21,24,28,29],nameerror:6,need:[5,6,15,23,24,25,28,29],need_releas:[6,15],neither:15,next:21,next_task:21,none:[3,6,14,15,21,22],nor:15,normal:[19,20,29],note:22,now:6,npm:23,number:[14,15,19,29],object:[3,6,7,10,12,14,15,21,22,24],objectid:[6,10,12,14,15,21,22,29],occupi:[6,15,25],occupy_devic:6,okai:28,old:21,on_messag:3,onc:24,one:[3,6,15,20,21,22,25,26],ones:6,onli:[3,5,6,24,25,28],only_idl:6,oper:25,option:[6,10,14,15,21,22,29],other:[12,19,29],our:25,out:7,over:[3,6,10,15,19,21,25,29],overal:22,overwrit:21,own:14,ownership:[6,19,29],packag:[1,25,27,28],page:[23,25],param:12,paramet:[1,3,6,10,15,16,21,24,25,29],parametererror:16,parent:[15,21],parent_device_nam:15,pars:7,pass:21,password:[1,28],pattern:12,paus:20,pend:[3,7,10,19,22,25,29],pip:23,place:25,platform:25,pleas:[23,24,28],port:[1,24,28],posit:[3,5,14,15,19,22,24,25,29],position_prefix:15,pre_task:21,preced:20,predefin:[12,25],prefix:15,prev:21,prev_task:21,prevent:[19,29],previou:[21,25],prioriti:[19,20,29],process:[3,10,14,25],project:25,project_root:28,prompt:22,prop:[3,6],proper:16,properli:15,properti:[3,5,6,19,24],provid:[6,21,25,28],purpos:23,push:23,put:[10,25],py:28,pydant:[9,15],pylint:23,pymongo:25,pyright:23,pytest:23,python:[21,23,25,28],queri:[6,15,21],query_properti:6,queue:[3,10],r:[23,26],rabbitmq:[1,3,23],rack:25,rais:[6,15,16],rang:12,raw:10,read:[1,7,25],readi:[6,20,21,25],real:[3,5,24,25],receiv:3,recommend:23,record:[12,25],redirect:3,refer:[21,23,24,25,26,28],regardless:6,regist:[5,14,19,28],registri:[5,14,19],relat:[4,8,13,18],releas:[5,6,15,19,29],release_devic:6,release_sample_posit:15,remot:[3,26],renam:21,renew:24,repo:[24,28],repositori:[23,25],repres:[19,25,29],represent:25,request:[3,6,7,9,15,19,20,22,25,29],request_devic:6,request_id:22,request_resourc:[19,29],request_sample_posit:15,request_user_input:22,requesting_resourc:20,requir:[5,10,21,23,25,26],rerout:19,reserv:[15,20],resourc:[15,19,20,25,28,29],respons:[7,22],result:[3,12,21],retrieve_user_input:22,retriv:22,ro:25,robot:25,rpc:3,run:[3,5,6,7,10,19,20,23,25,28,29],run_program:[19,29],run_subtask:19,run_task:16,s:[6,12,15,21,25,29],same:[6,15,19,21,29],sampl:[0,5,6,7,9,10,12,13,15,19,21,22,24,25,29],sample_1:29,sample_2:29,sample_3:29,sample_4:29,sample_amount:12,sample_id:[10,14,15,21,29],sample_posit:[5,15,19,24,29],sample_position_prefix:15,sample_view:[0,5,24,27],sampleposit:[5,14,15,24],samplepositionrequest:15,samplepositionslock:15,samplepositionstatu:15,sampleview:15,scan:7,search:[6,25],section:28,see:10,self:[5,19,21,24,29],semant:23,send:[3,19,29],sensor:12,sent:20,separ:14,serv:28,server:3,set:[5,6,15,23,24,26],set_messag:[5,6],setpoint:[19,29],setter:5,shall:6,sharabl:25,share:[19,25,29],should:[5,6,9,19,21,24,25,28,29],signal:12,signifi:6,similar:29,simpli:25,sinc:25,singl:15,skip:15,snippet:25,so:[5,6,19,21,23,24,25,29],some:[5,6,12,15,20,21,24,25,28],someth:25,soon:26,sourc:[1,3,5,6,7,9,10,12,14,15,16,19,20,21,22,24,29],specif:6,specifi:[5,6,15,24,25,28],start:[3,7,20,21,25],startwith:15,state:6,statu:[3,6,10,15,16,20,21,22],still:[6,25],stop:[5,20,24,25],store:[5,21,24,28],str:[3,5,6,10,12,14,15,19,21,22,24],string:[12,14,22],structur:[3,15],submit:[7,10,20,25],submodul:27,subpackag:27,subtask:[19,21],subtask_id:21,subtask_typ:21,success:3,supported_sample_posit:19,sure:23,sync:6,sync_device_statu:6,synthesi:25,system:[6,12,22,24,25,28],system_log:12,t:[5,24],take:[12,19,29],target:28,task:[0,3,6,7,9,10,12,14,15,16,18,20,21,22,26,28],task_1:28,task_2:28,task_3:28,task_actor:[0,27],task_entri:21,task_enum:[0,18],task_id:[3,6,10,12,14,15,19,21,22,29],task_manag:[0,16,27],task_result:21,task_typ:21,task_view:[0,27],taskprior:[19,20,29],taskstatu:[20,21],taskview:21,tell:15,temperatur:[12,19,25,29],temporari:[5,24],test:23,than:12,them:[5,24,25,28],thi:[1,3,5,6,7,9,10,12,14,15,19,21,22,24,25,26,28,29],thing:[4,8,13,18],through:[22,25],throughout:25,time:[5,7,12,24],timeout:3,toml:28,track:[23,25],trai:15,transfer:[5,24],translat:21,try_to_mark_task_readi:21,tupl:[15,29],two:25,txt:[23,26],type:[1,3,5,6,10,12,14,15,19,21,22,23,24],type_or_nam:6,uid:15,under:25,union:[12,15,21],uniqu:[5,6,14,24],unit:23,unknown:6,unlock:15,unoccupi:15,until:[15,19,21,22,29],up:[5,6,23,24,26],updat:[10,15,16,21,22,25],update_experiment_statu:10,update_request_statu:22,update_result:21,update_sample_task_id:[10,15],update_statu:21,update_subtask_result:21,update_subtask_statu:21,update_task_depend:21,urgent:20,us:[3,5,6,10,15,16,19,21,23,24,25,28,29],usabl:6,user:[5,6,9,10,20,22,24,25],user_input:[0,27],userinputview:22,usernam:[1,28],userrequeststatu:22,usual:[6,28],valid:15,valu:[3,6,10,12,15,20,22,25],valueerror:[6,15],vertex:25,via:[3,23,25],view:[6,10,15,21,22,25],voltag:12,wait:[20,25],want:23,warn:12,we:[5,6,10,12,15,19,21,23,24,25,26,28,29],websit:25,weight:12,well:[6,25],what:25,when:[5,6,7,15,16,19,24,25,29],where:[5,12,24,28],whether:[5,6,15,21],which:[1,3,5,6,10,12,14,15,19,21,22,24,25,28,29],within:[12,15,21],work:[25,28],worker:16,workflow:[12,25],working_dir:[1,28],wrap:3,wrapper:[3,6,10,15,21,25],write:[9,24],wrong:16,wrote:12,xrd:12,yaml:1,yarn:23,yet:20,you:[15,19,23,24,25,26,28,29],your:[24,28]},titles:["alab_management package","alab_management.config module","alab_management.data_explorer package","alab_management.device_manager module","alab_management.device_view package","alab_management.device_view.device module","alab_management.device_view.device_view module","alab_management.experiment_manager module","alab_management.experiment_view package","alab_management.experiment_view.experiment module","alab_management.experiment_view.experiment_view module","alab_management.lab_view module","alab_management.logger module","alab_management.sample_view package","alab_management.sample_view.sample module","alab_management.sample_view.sample_view module","alab_management.task_actor module","alab_management.task_manager module","alab_management.task_view package","alab_management.task_view.task module","alab_management.task_view.task_enums module","alab_management.task_view.task_view module","alab_management.user_input module","Development","Defining a new device","Overview","Installation","alab_management","Set up definition folder","Defining a new task"],titleterms:{"new":[24,29],actor:25,alab_manag:[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,27],ci:23,code:26,command:28,commit:23,config:1,configur:28,content:[0,2,4,8,13,18],data:25,data_explor:2,defin:[24,29],definit:28,develop:23,devic:[5,24],device_manag:3,device_view:[4,5,6],environ:23,experi:[9,25],experiment_manag:7,experiment_view:[8,9,10],file:28,folder:28,from:26,git:23,indic:25,initi:28,instal:26,lab:25,lab_view:11,line:28,logger:12,manag:25,modul:[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,25],next:[26,28],overview:25,packag:[0,2,4,8,13,18],pip:26,prerequisit:26,project:28,rule:23,s:[26,28],sampl:14,sample_view:[13,14,15],set:28,setup:23,sourc:26,statu:25,storag:25,structur:28,submodul:[0,4,8,13,18],subpackag:0,system:23,tabl:25,task:[19,25,29],task_actor:16,task_enum:20,task_manag:17,task_view:[18,19,20,21],terminolog:25,up:28,user_input:22,via:[26,28],what:[26,28]}})