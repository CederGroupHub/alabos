Search.setIndex({docnames:["alab_management","alab_management.builders","alab_management.builders.experimentbuilder","alab_management.builders.samplebuilder","alab_management.config","alab_management.device_manager","alab_management.device_view","alab_management.device_view.dbattributes","alab_management.device_view.device","alab_management.device_view.device_view","alab_management.experiment_manager","alab_management.experiment_view","alab_management.experiment_view.experiment","alab_management.experiment_view.experiment_view","alab_management.lab_view","alab_management.logger","alab_management.sample_view","alab_management.sample_view.sample","alab_management.sample_view.sample_view","alab_management.task_actor","alab_management.task_manager","alab_management.task_view","alab_management.task_view.task","alab_management.task_view.task_enums","alab_management.task_view.task_view","alab_management.user_input","development","device_definition","index","installation","modules","setup","task_definition"],envversion:{"sphinx.domains.c":2,"sphinx.domains.changeset":1,"sphinx.domains.citation":1,"sphinx.domains.cpp":5,"sphinx.domains.index":1,"sphinx.domains.javascript":2,"sphinx.domains.math":2,"sphinx.domains.python":3,"sphinx.domains.rst":2,"sphinx.domains.std":2,"sphinx.ext.intersphinx":1,"sphinx.ext.todo":2,"sphinx.ext.viewcode":1,sphinx:56},filenames:["alab_management.rst","alab_management.builders.rst","alab_management.builders.experimentbuilder.rst","alab_management.builders.samplebuilder.rst","alab_management.config.rst","alab_management.device_manager.rst","alab_management.device_view.rst","alab_management.device_view.dbattributes.rst","alab_management.device_view.device.rst","alab_management.device_view.device_view.rst","alab_management.experiment_manager.rst","alab_management.experiment_view.rst","alab_management.experiment_view.experiment.rst","alab_management.experiment_view.experiment_view.rst","alab_management.lab_view.rst","alab_management.logger.rst","alab_management.sample_view.rst","alab_management.sample_view.sample.rst","alab_management.sample_view.sample_view.rst","alab_management.task_actor.rst","alab_management.task_manager.rst","alab_management.task_view.rst","alab_management.task_view.task.rst","alab_management.task_view.task_enums.rst","alab_management.task_view.task_view.rst","alab_management.user_input.rst","development.rst","device_definition.rst","index.rst","installation.rst","modules.rst","setup.rst","task_definition.rst"],objects:{"":[[0,0,0,"-","alab_management"]],"alab_management.builders":[[2,0,0,"-","experimentbuilder"],[3,0,0,"-","samplebuilder"]],"alab_management.builders.experimentbuilder":[[2,1,1,"","ExperimentBuilder"]],"alab_management.builders.experimentbuilder.ExperimentBuilder":[[2,2,1,"","add_sample"],[2,2,1,"","add_task"],[2,2,1,"","generate_input_file"],[2,2,1,"","plot"],[2,2,1,"","to_dict"]],"alab_management.builders.samplebuilder":[[3,1,1,"","SampleBuilder"]],"alab_management.builders.samplebuilder.SampleBuilder":[[3,2,1,"","add_task"],[3,3,1,"","tasks"],[3,2,1,"","to_dict"]],"alab_management.config":[[4,4,1,"","froze_config"]],"alab_management.device_manager":[[5,1,1,"","DeviceManager"],[5,1,1,"","DeviceMethodCallState"],[5,1,1,"","DeviceWrapper"],[5,1,1,"","DevicesClient"],[5,1,1,"","MethodCallStatus"]],"alab_management.device_manager.DeviceManager":[[5,2,1,"","on_message"],[5,2,1,"","run"]],"alab_management.device_manager.DeviceMethodCallState":[[5,5,1,"","future"],[5,5,1,"","last_updated"],[5,5,1,"","status"]],"alab_management.device_manager.DeviceWrapper":[[5,1,1,"","DeviceMethodWrapper"],[5,3,1,"","name"]],"alab_management.device_manager.DeviceWrapper.DeviceMethodWrapper":[[5,3,1,"","method"]],"alab_management.device_manager.DevicesClient":[[5,2,1,"","call"],[5,2,1,"","create_device_wrapper"],[5,2,1,"","on_message"]],"alab_management.device_manager.MethodCallStatus":[[5,5,1,"","FAILURE"],[5,5,1,"","IN_PROGRESS"],[5,5,1,"","PENDING"],[5,5,1,"","SUCCESS"]],"alab_management.device_view":[[7,0,0,"-","dbattributes"],[8,0,0,"-","device"],[9,0,0,"-","device_view"]],"alab_management.device_view.dbattributes":[[7,1,1,"","DictInDatabase"],[7,1,1,"","ListInDatabase"],[7,4,1,"","value_in_database"]],"alab_management.device_view.dbattributes.DictInDatabase":[[7,2,1,"","apply_default_value"],[7,2,1,"","as_normal_dict"],[7,2,1,"","clear"],[7,2,1,"","copy"],[7,3,1,"","db_filter"],[7,3,1,"","db_projection"],[7,2,1,"","fromkeys"],[7,2,1,"","get"],[7,2,1,"","items"],[7,2,1,"","keys"],[7,2,1,"","pop"],[7,2,1,"","popitem"],[7,2,1,"","setdefault"],[7,2,1,"","update"],[7,2,1,"","values"]],"alab_management.device_view.dbattributes.ListInDatabase":[[7,2,1,"","append"],[7,2,1,"","apply_default_value"],[7,2,1,"","clear"],[7,2,1,"","copy"],[7,2,1,"","count"],[7,3,1,"","db_filter"],[7,3,1,"","db_projection"],[7,2,1,"","extend"],[7,2,1,"","index"],[7,2,1,"","insert"],[7,2,1,"","pop"],[7,2,1,"","remove"],[7,2,1,"","reverse"],[7,2,1,"","sort"]],"alab_management.device_view.device":[[27,1,1,"","BaseDevice"],[8,1,1,"","DeviceSignalEmitter"],[8,4,1,"","add_device"],[8,4,1,"","get_all_devices"],[8,4,1,"","log_signal"]],"alab_management.device_view.device.BaseDevice":[[27,2,1,"","__init__"],[8,2,1,"","connect"],[27,5,1,"","description"],[8,2,1,"","dict_in_database"],[8,2,1,"","disconnect"],[27,2,1,"","emergent_stop"],[8,2,1,"","get_message"],[8,2,1,"","is_running"],[8,2,1,"","list_in_database"],[8,2,1,"","request_maintenance"],[8,2,1,"","retrieve_signal"],[27,3,1,"","sample_positions"],[8,2,1,"","set_message"]],"alab_management.device_view.device.DeviceSignalEmitter":[[8,2,1,"","get_methods_to_log"],[8,2,1,"","log_method_to_db"],[8,2,1,"","retrieve_signal"],[8,2,1,"","start"],[8,2,1,"","stop"]],"alab_management.device_view.device_view":[[9,6,1,"","DeviceConnectionError"],[9,1,1,"","DevicePauseStatus"],[9,1,1,"","DeviceTaskStatus"],[9,1,1,"","DeviceView"]],"alab_management.device_view.device_view.DevicePauseStatus":[[9,5,1,"","PAUSED"],[9,5,1,"","RELEASED"],[9,5,1,"","REQUESTED"]],"alab_management.device_view.device_view.DeviceTaskStatus":[[9,5,1,"","ERROR"],[9,5,1,"","IDLE"],[9,5,1,"","OCCUPIED"],[9,5,1,"","UNKNOWN"]],"alab_management.device_view.device_view.DeviceView":[[9,2,1,"","add_devices_to_db"],[9,2,1,"","execute_command"],[9,2,1,"","get_all"],[9,2,1,"","get_all_attributes"],[9,2,1,"","get_attribute"],[9,2,1,"","get_available_devices"],[9,2,1,"","get_device"],[9,2,1,"","get_devices_by_task"],[9,2,1,"","get_message"],[9,2,1,"","get_samples_on_device"],[9,2,1,"","get_status"],[9,2,1,"","occupy_device"],[9,2,1,"","pause_device"],[9,2,1,"","query_property"],[9,2,1,"","release_device"],[9,2,1,"","request_devices"],[9,2,1,"","set_all_attributes"],[9,2,1,"","set_attribute"],[9,2,1,"","set_message"],[9,2,1,"","sync_device_status"],[9,2,1,"","unpause_device"]],"alab_management.experiment_manager":[[10,1,1,"","ExperimentManager"]],"alab_management.experiment_manager.ExperimentManager":[[10,2,1,"","handle_pending_experiments"],[10,2,1,"","mark_completed_experiments"],[10,2,1,"","run"]],"alab_management.experiment_view":[[12,0,0,"-","experiment"],[13,0,0,"-","experiment_view"]],"alab_management.experiment_view.experiment":[[12,1,1,"","InputExperiment"]],"alab_management.experiment_view.experiment.InputExperiment":[[12,5,1,"","name"],[12,5,1,"","samples"],[12,5,1,"","tasks"]],"alab_management.experiment_view.experiment_view":[[13,1,1,"","ExperimentStatus"],[13,1,1,"","ExperimentView"]],"alab_management.experiment_view.experiment_view.ExperimentStatus":[[13,5,1,"","COMPLETED"],[13,5,1,"","ERROR"],[13,5,1,"","PENDING"],[13,5,1,"","RUNNING"]],"alab_management.experiment_view.experiment_view.ExperimentView":[[13,2,1,"","create_experiment"],[13,2,1,"","get_experiment"],[13,2,1,"","get_experiment_by_sample_id"],[13,2,1,"","get_experiment_by_task_id"],[13,2,1,"","get_experiments_with_status"],[13,2,1,"","update_experiment_status"],[13,2,1,"","update_sample_task_id"]],"alab_management.logger":[[15,1,1,"","DBLogger"],[15,1,1,"","LoggingLevel"],[15,1,1,"","LoggingType"]],"alab_management.logger.DBLogger":[[15,2,1,"","filter_device_signal"],[15,2,1,"","filter_log"],[15,2,1,"","get_latest_device_signal"],[15,2,1,"","log"],[15,2,1,"","log_amount"],[15,2,1,"","log_characterization_result"],[15,2,1,"","log_device_signal"],[15,2,1,"","system_log"]],"alab_management.logger.LoggingLevel":[[15,5,1,"","CRITICAL"],[15,5,1,"","DEBUG"],[15,5,1,"","ERROR"],[15,5,1,"","FATAL"],[15,5,1,"","INFO"],[15,5,1,"","WARN"],[15,5,1,"","WARNING"]],"alab_management.logger.LoggingType":[[15,5,1,"","CHARACTERIZATION_RESULT"],[15,5,1,"","DEVICE_SIGNAL"],[15,5,1,"","OTHER"],[15,5,1,"","SAMPLE_AMOUNT"],[15,5,1,"","SYSTEM_LOG"]],"alab_management.sample_view":[[17,0,0,"-","sample"],[18,0,0,"-","sample_view"]],"alab_management.sample_view.sample":[[17,1,1,"","Sample"],[17,1,1,"","SamplePosition"],[17,4,1,"","add_standalone_sample_position"],[17,4,1,"","get_all_standalone_sample_positions"]],"alab_management.sample_view.sample.Sample":[[17,5,1,"","name"],[17,5,1,"","position"],[17,5,1,"","sample_id"],[17,5,1,"","task_id"]],"alab_management.sample_view.sample.SamplePosition":[[17,5,1,"","SEPARATOR"],[17,5,1,"","description"],[17,5,1,"","name"],[17,5,1,"","number"]],"alab_management.sample_view.sample_view":[[18,1,1,"","SamplePositionRequest"],[18,1,1,"","SamplePositionStatus"],[18,1,1,"","SampleView"]],"alab_management.sample_view.sample_view.SamplePositionRequest":[[18,1,1,"","Config"],[18,2,1,"","from_py_type"],[18,2,1,"","from_str"],[18,5,1,"","number"],[18,5,1,"","prefix"]],"alab_management.sample_view.sample_view.SamplePositionRequest.Config":[[18,5,1,"","extra"]],"alab_management.sample_view.sample_view.SamplePositionStatus":[[18,5,1,"","EMPTY"],[18,5,1,"","LOCKED"],[18,5,1,"","OCCUPIED"]],"alab_management.sample_view.sample_view.SampleView":[[18,2,1,"","add_sample_positions_to_db"],[18,2,1,"","clean_up_sample_position_collection"],[18,2,1,"","create_sample"],[18,2,1,"","get_available_sample_position"],[18,2,1,"","get_sample"],[18,2,1,"","get_sample_position"],[18,2,1,"","get_sample_position_parent_device"],[18,2,1,"","get_sample_position_status"],[18,2,1,"","get_sample_positions_by_task"],[18,2,1,"","is_unoccupied_position"],[18,2,1,"","lock_sample_position"],[18,2,1,"","move_sample"],[18,2,1,"","release_sample_position"],[18,2,1,"","request_sample_positions"],[18,2,1,"","update_sample_task_id"]],"alab_management.task_actor":[[19,6,1,"","ParameterError"]],"alab_management.task_view":[[22,0,0,"-","task"],[23,0,0,"-","task_enums"],[24,0,0,"-","task_view"]],"alab_management.task_view.task":[[32,1,1,"","BaseTask"],[22,4,1,"","add_reroute_task"],[22,4,1,"","add_task"],[22,4,1,"","get_all_tasks"]],"alab_management.task_view.task.BaseTask":[[32,2,1,"","__init__"],[22,2,1,"","add_to"],[22,2,1,"","get_message"],[22,3,1,"","is_simulation"],[22,3,1,"","priority"],[32,2,1,"","run"],[22,2,1,"","run_subtask"],[22,3,1,"","samples"],[22,2,1,"","set_message"],[32,2,1,"","validate"]],"alab_management.task_view.task_enums":[[23,1,1,"","TaskPriority"],[23,1,1,"","TaskStatus"]],"alab_management.task_view.task_enums.TaskPriority":[[23,5,1,"","HIGH"],[23,5,1,"","LOW"],[23,5,1,"","NORMAL"],[23,5,1,"","SYSTEM"],[23,5,1,"","URGENT"]],"alab_management.task_view.task_enums.TaskStatus":[[23,5,1,"","COMPLETED"],[23,5,1,"","ERROR"],[23,5,1,"","INITIATED"],[23,5,1,"","PAUSED"],[23,5,1,"","READY"],[23,5,1,"","REQUESTING_RESOURCES"],[23,5,1,"","RUNNING"],[23,5,1,"","STOPPED"],[23,5,1,"","WAITING"]],"alab_management.task_view.task_view":[[24,1,1,"","TaskView"]],"alab_management.task_view.task_view.TaskView":[[24,2,1,"","create_subtask"],[24,2,1,"","create_task"],[24,2,1,"","encode_task"],[24,2,1,"","get_ready_tasks"],[24,2,1,"","get_status"],[24,2,1,"","get_task"],[24,2,1,"","get_task_with_sample"],[24,2,1,"","get_tasks_by_status"],[24,2,1,"","set_message"],[24,2,1,"","try_to_mark_task_ready"],[24,2,1,"","update_result"],[24,2,1,"","update_status"],[24,2,1,"","update_subtask_result"],[24,2,1,"","update_subtask_status"],[24,2,1,"","update_task_dependency"]],"alab_management.user_input":[[25,1,1,"","UserInputView"],[25,1,1,"","UserRequestStatus"],[25,4,1,"","request_maintenance_input"],[25,4,1,"","request_user_input"]],"alab_management.user_input.UserInputView":[[25,2,1,"","clean_up_user_input_collection"],[25,2,1,"","get_all_pending_requests"],[25,2,1,"","get_request"],[25,2,1,"","insert_request"],[25,2,1,"","retrieve_user_input"],[25,2,1,"","update_request_status"]],"alab_management.user_input.UserRequestStatus":[[25,5,1,"","ERROR"],[25,5,1,"","FULLFILLED"],[25,5,1,"","PENDING"]],alab_management:[[1,0,0,"-","builders"],[4,0,0,"-","config"],[5,0,0,"-","device_manager"],[6,0,0,"-","device_view"],[10,0,0,"-","experiment_manager"],[11,0,0,"-","experiment_view"],[15,0,0,"-","logger"],[16,0,0,"-","sample_view"],[19,0,0,"-","task_actor"],[21,0,0,"-","task_view"],[25,0,0,"-","user_input"]]},objnames:{"0":["py","module","Python module"],"1":["py","class","Python class"],"2":["py","method","Python method"],"3":["py","property","Python property"],"4":["py","function","Python function"],"5":["py","attribute","Python attribute"],"6":["py","exception","Python exception"]},objtypes:{"0":"py:module","1":"py:class","2":"py:method","3":"py:property","4":"py:function","5":"py:attribute","6":"py:exception"},terms:{"0":[7,22,32],"1":[5,7,9,13,15,17,18,23],"10":[15,23],"100":23,"16":[8,27],"1d":15,"1h":15,"2":[5,9,13,15,18,23],"20":[15,23],"27017":[4,31],"2ca31f7c5ef4":7,"3":[5,9,13,15,18,23],"30":[15,23],"3c79e5035567c8ef3267":26,"4":[5,9,13,15,22,23,32],"40":15,"4624":7,"48b1":7,"5":[7,15,23],"50":15,"502":27,"5672":4,"6":23,"7":23,"8":[8,23,27],"9":23,"900":23,"abstract":[8,22,27,28,32],"case":8,"class":[2,3,5,7,8,9,10,12,13,15,17,18,22,23,24,25,27,28,32],"default":[7,8,18,31],"do":28,"enum":[5,9,13,15,18,23,25],"float":[5,32],"function":[2,5,7,9,15,18,19,22,27,28,32],"import":[7,28],"int":[8,15,17,22,27],"long":18,"new":[7,18,24],"return":[2,3,4,5,7,8,9,13,15,17,18,22,24,25,27,32],"short":8,"super":[7,27,32],"true":[5,9,22,25,32],"try":[18,22,24,32],"while":[22,32],A:[2,5,8,13,15,17,18,28,31],At:13,By:18,For:[22,27,28,31,32],If:[9,18,24,31,32],In:[22,28,32],It:[2,4,8,10,19,24,27,28],One:22,The:[2,5,8,9,13,17,18,19,22,23,27,28,31,32],There:9,To:[26,27,29,31,32],With:28,_:18,__exit__:[9,18],__init__:[7,27,31,32],_a:18,_base:5,_bodi:5,_check_statu:5,_id:24,_sampl:12,_task:12,abc:[8,22],about:[8,22,27,32],access:[5,8,29],accord:31,across:[7,18],act:8,action:26,actor:23,actual:18,acycl:28,adapt:5,add:[2,13,22,24,26],add_devic:8,add_devices_to_db:9,add_reroute_task:22,add_sampl:2,add_sample_positions_to_db:18,add_standalone_sample_posit:17,add_task:[2,3,22],add_to:22,addit:2,address:27,administ:5,aim:28,alab:[7,10,28,31],alab_manag:[26,27,29,32],alabo:[7,8,31],all:[4,5,7,8,9,17,18,22,24,25,27,28,32],alloc:[22,32],allow:[4,28],alreadi:[9,18],also:[13,22,24,26,28,31,32],amount:15,an:[2,4,5,8,9,13,22,27,28,32],ani:[2,3,5,7,8,9,10,13,15,18,22,24,25,27,32],apart:26,api:9,appear:[9,18],append:[7,22],apply_default_valu:7,appropri:8,ar:[7,8,9,10,18,22,23,24,27,28,32],architectur:28,arg:[5,7,8,9,22,27,32],argument:[2,5],as_normal_dict:7,assign:[13,22,24,28,31,32],attach:2,attribut:[7,8,9,27,32],attribute_in_databas:7,attribute_nam:7,attributeerror:9,authent:31,automat:[22,31,32],autonom:[0,28],avail:[9,18,22,32],ax:2,back:[5,8,15],base:[2,3,5,7,8,9,10,12,13,15,17,18,19,22,23,24,25],basedevic:[7,8,9,27,28],basemodel:[12,18],basetask:[22,24,28,32],basic:[5,15,17,28],batch:28,batteri:15,be8b61e:7,becaus:8,been:[13,17,23],befor:[7,22,24,26,31,32],being:32,besid:31,between:28,bf7a:7,block:25,bool:[8,9,18,22,24,25,32],both:18,briefli:17,bson:17,builder:[0,30],call:[5,7,8,9,18,19,22,32],callabl:9,callback:5,can:[2,5,8,15,17,18,22,24,26,27,28,31,32],cannot:[22,23,24,32],cd:[26,29],cedergrouphub:[26,29],certain:[5,15,28],chang:26,channel:5,character:15,characterization_result:15,charg:15,check:[8,18,24,26],chemic:[15,28],classmethod:18,classvar:17,clean_up_sample_position_collect:18,clean_up_user_input_collect:25,clear:7,client:5,clone:[26,29],code:[26,27,28],collect:[9,10,13,18,24,25,28],com:[5,26,29],come:[15,29],command:[2,5,22,26,32],commun:[9,26,28],complet:[10,13,22,23,24,25,28,32],concurr:5,conduct:[5,28],config:[0,18,30,31],config_:4,configur:[4,28],conflict:[22,32],connect:[8,9,27,31],connect_to_devic:9,constrainedintvalu:18,constrainedstrvalu:12,construct:[22,28],consum:9,contain:[4,13,15,24,28],content:30,context:[22,32],conveni:24,convert:4,convien:24,coordin:[8,17,27],copi:7,correct:[7,23],correctli:26,correspond:[24,32],count:7,creat:[5,7,8,13,18,24,28],create_device_wrapp:5,create_experi:13,create_sampl:18,create_subtask:24,create_task:24,creation:13,critic:15,current:[8,9,17,22,23,24,26,28,32],custom:[15,27,29,31,32],cycl:28,dag:28,dashboard:[8,9,22,24,25],data:[4,12,15,18,22,32],databas:[7,8,9,10,12,13,15,17,18,19,22,24,25,28,29,31,32],datetim:8,db:[7,9,18,31],db_filter:7,db_project:7,dbattribut:[0,6],dblogger:15,debug:15,decid:9,declar:[7,8],decor:8,def:[7,8,27,32],default_lab:4,default_valu:[7,8],defin:[5,7,8,12,17,18,22,28,31],definit:[9,17,28,29],depend:[8,26,28],deriv:32,describ:[8,17,27,28],descript:[8,9,17,18,27],dest:[22,32],dev:26,devic:[0,5,6,7,9,15,17,18,22,28,29,31,32],device_1:31,device_2:31,device_3:31,device_collect:7,device_manag:[0,30],device_nam:[5,7,8,9,15],device_names_str:9,device_rpc:5,device_sign:15,device_str:9,device_typ:9,device_type_nam:9,device_type_str:9,device_types_str:9,device_view:[0,30],deviceconnectionerror:9,devicemanag:5,devicemethodcallst:5,devicemethodwrapp:5,devicepausestatu:9,devices_and_posit:[22,32],devices_cli:5,devicescli:5,devicesignalemitt:8,deviceslock:9,devicetaskstatu:9,deviceview:9,devicewrapp:[5,8],dict:[3,4,5,7,8,9,13,15,17,18,22,24,25],dict_in_databas:[7,8],dictindatabas:[7,8],dictionari:[2,8,15],die:28,differ:15,dir:31,direct:28,directli:5,directori:31,disconnect:8,discuss:29,displai:[8,22,24],doe:[8,27],doesn:[8,27],done:[10,13,28],dramatiq:[19,28],driver:[5,27,28],drop:[18,25],dump:24,duplic:9,dure:[15,22,23],e:[7,15,22,26,28,29,32],each:28,easili:[26,28],els:[15,18],emerg:[8,27],emergent_stop:[8,27],empti:[8,18,28,31],emul:7,encod:24,encode_task:24,encount:23,end:28,ensur:7,entri:[9,18,24],enumer:5,ericavonb:26,error:[9,13,15,18,23,25],etc:[8,28],even:[8,18,28],event:10,everi:5,everyth:0,exampl:[4,7,8,15,22,27,31,32],except:[9,19],execut:[5,9,15,22,23,32],execute_command:9,executor:10,exist:18,exp_id:13,experi:[0,2,3,10,11,13,22,32],experiment_manag:[0,30],experiment_view:[0,30],experimentbuild:[0,1],experimentmanag:10,experimentstatu:13,experimentview:13,extend:7,extens:28,extra:18,factori:7,fail:9,failur:5,fals:[7,9,22,24,25,32],far:[8,15],fatal:15,feed:5,file:[2,4],filenam:2,filter:13,filter_device_sign:15,filter_log:15,find:[10,15],finish:[10,23,24],first:[7,26,32],five:28,flag:10,flake8:26,flexibl:28,fmt:2,folder:29,follow:[4,12,26,31],forbid:18,form:[8,15],format:[12,13,26,28],found:[7,9,18,24],from:[4,5,7,8,10,15,22,24,25,26,27,28,32],from_py_typ:18,from_str:18,fromkei:7,froze_config:4,frozen:4,frozen_config:4,fulfil:25,fullfil:25,furnac:[8,15,22,27,32],furnace_1:18,furnace_t:[8,27],furnacecontrol:27,futur:[5,7],g:[15,26,28],gener:[2,4,9,31],generate_input_fil:2,geograph:17,get:[4,5,7,8,9,13,15,17,18,22,24,25,32],get_al:9,get_all_attribut:9,get_all_devic:8,get_all_pending_request:25,get_all_standalone_sample_posit:17,get_all_task:22,get_attribut:9,get_available_devic:9,get_available_sample_posit:18,get_devic:9,get_devices_by_task:9,get_experi:13,get_experiment_by_sample_id:13,get_experiment_by_task_id:13,get_experiments_with_statu:13,get_latest_device_sign:15,get_messag:[8,9,22],get_methods_to_log:8,get_ready_task:24,get_request:25,get_sampl:18,get_sample_posit:18,get_sample_position_parent_devic:18,get_sample_position_statu:18,get_sample_positions_by_task:18,get_samples_on_devic:9,get_statu:[9,24],get_task:24,get_task_with_sampl:24,get_tasks_by_statu:24,get_temperatur:[22,32],getter:8,gist:26,git:[28,29],github:[5,26,28,29],give:25,given:[9,13,18,24,25],global:26,graph:28,great:28,ha:[9,13,17,18,22,23,28,31,32],handl:[5,7,24,31],handle_pending_experi:10,have:[7,9,22,28,29],heat:[8,22,27,28,32],here:[8,22,26,27,32],high:[22,23,32],higher:[15,23],highli:26,hold:[5,8,17,27,28],host:[4,28,31],hot:32,how:[8,15,22,27,29,31,32],http:[5,26],i:[7,22,32],id:[9,13,17,18,22,24,25,28,32],identifi:[8,9,17,27,32],idl:[9,28],ie:18,implement:28,imposs:[22,32],in_progress:5,includ:[8,9,18,27],incom:10,index:[7,28],indic:[9,18],info:[15,18,24],inform:[8,15,26,27,28],inherit:[8,22,24,27,28,32],init:31,initi:[7,17,19,23,27],input:[2,25],inputexperi:[12,13],insert:[7,9,13,18,24,25],insert_request:25,insid:[5,8,22,27,32],inside_furnac:[22,32],instal:26,instanc:[5,8,17,18,28],instanti:[7,28],instead:8,integ:23,intend:[8,13],intenum:23,interest:24,interv:8,interval_second:8,introduc:31,invalid:32,involvend:32,is_run:[8,22,32],is_simul:22,is_unoccupied_posit:18,item:7,iter:15,its:[9,13,18,24,28],itself:31,job:24,json:2,just:[8,18,28,31],kei:7,keyword:[2,5],kind:[8,27],kwarg:[5,7,8,9,18,22,27,32],lab:[0,8,13,17,22,27,31,32],lab_view:[0,22,30,32],labview:[13,32],larger:23,last:15,last_upd:5,later:13,launch:[19,28],least:29,level:15,life:28,like:[8,9,28,31],list:[2,5,7,8,9,12,13,15,18,22,24,25,27,28,32],list_in_databas:[7,8],listen:5,listindatabas:[7,8],load:31,local:29,localhost:[4,31],lock:[18,28],lock_sample_posit:18,log:[8,15,22,32],log_amount:15,log_characterization_result:15,log_data:15,log_device_sign:[8,15,22,32],log_method_to_db:8,log_sign:8,logger:[0,22,30,32],logging_typ:15,logginglevel:15,loggingtyp:15,look:[18,31],loop:10,low:23,m:31,mai:[9,26,28,31],main:[12,18,28],mainten:[9,25],make:[8,22,26,32],manag:[0,5,10,13,18,22,24,25,31,32],mani:10,manipul:24,manual:[7,8,27],map:[8,27],mappingproxi:4,mark:[10,24,25],mark_completed_experi:10,match:[8,18],matter:[8,27],maus:5,messag:[5,8,9,22,24,26],metadata:[2,3],method:[5,8,9,10,13,18,24,27,32],method_fram:5,method_handl:5,method_nam:8,methodcallstatu:5,might:[22,32],mirror:7,modifi:4,modul:[30,31],mongodb:[4,24,26,28,29],more:[22,26,27,31],move:[22,28,32],move_sampl:18,moving_task:[22,32],multipl:28,must:[2,7,8,24,28,29,31,32],my_attribut:7,mydevic:7,mydevice_1:7,name:[2,3,4,5,7,8,9,12,15,17,18,22,24,27,31,32],nameerror:9,need:[8,9,18,26,27,28,31,32],need_releas:[9,18],neither:18,nest:8,next:24,next_task:24,none:[2,3,5,7,8,9,17,18,22,24,25,27,32],nor:18,normal:[8,22,23,32],note:[7,8,25],now:9,npm:26,number:[8,17,18,22,27,32],object:[2,3,5,7,8,9,10,13,15,17,18,24,25,27],objectid:[9,13,15,17,18,24,25,32],occupi:[9,18,28],occupy_devic:9,occur:7,okai:31,old:24,on_messag:5,onc:27,one:[5,9,18,23,24,25,28,29],ones:9,onli:[5,7,8,9,27,28,31],only_idl:9,oper:[9,28],option:[8,9,13,15,17,18,24,25,32],order:7,other:[15,22,32],our:28,out:[7,10],outsid:9,over:[5,9,13,18,22,24,28,32],overal:25,overwrit:24,own:17,ownership:[9,22,32],packag:[4,28,30,31],page:[26,28],param:15,paramet:[2,4,5,7,8,9,13,15,18,19,22,24,27,28,32],parametererror:19,parent:[18,24],parent_device_nam:18,pars:10,pass:[8,24],password:[4,31],pattern:15,paus:[9,23],pause_devic:9,pend:[5,10,13,22,25,28,32],perform:32,persist:7,pip:26,place:28,platform:28,pleas:[26,27,31],plot:2,pop:7,popitem:7,port:[4,27,31],posit:[5,8,17,18,22,25,27,28,32],position_prefix:18,pre_task:24,preced:23,predefin:[15,28],prefix:18,pressur:8,prev:24,prev_task:24,prevent:[22,32],previou:[24,28],prioriti:[22,23,32],process:[5,8,13,17,28],project:28,project_root:31,prompt:[8,25],prop:[5,9],proper:19,properli:18,properti:[3,5,7,8,9,22,27],provid:[8,9,24,28,31],pull:8,purpos:26,push:26,put:[13,28],py:31,pydant:[12,18],pylint:26,pymongo:28,pyright:26,pytest:26,python:[8,24,26,28,31],queri:[7,9,18,24],query_properti:9,queue:[5,9,13],r:[26,29],rabbitmq:[4,5,26],rack:28,rais:[7,9,18,19],rang:15,raw:13,read:[4,10,28],readi:[9,23,24,28],real:[5,8,27,28],receiv:5,recommend:26,record:[15,28],redirect:5,refer:[24,26,27,28,29,31],refil:9,regardless:9,regist:[8,17,22,31],registri:[8,17,22],rel:8,relat:[6,11,16,21],releas:[8,9,18,22,32],release_devic:9,release_sample_posit:18,remot:[5,29],remov:7,renam:24,renew:27,repo:[27,31],repositori:[26,28],repres:[22,28,32],represent:28,request:[5,9,10,12,18,22,23,25,28,32],request_devic:9,request_id:25,request_mainten:8,request_maintenance_input:25,request_resourc:[22,32],request_sample_posit:18,request_user_input:25,requesting_resourc:23,requir:[8,13,24,26,28,29,32],rerout:22,reserv:[18,23,32],resourc:[18,22,23,28,31,32],respect:8,respons:[10,25],result:[5,8,15,22,24],retriev:[7,8,9,15],retrieve_sign:8,retrieve_user_input:25,retriv:25,revers:7,ro:28,robot:28,role:32,rpc:5,run:[5,8,9,10,13,22,23,26,28,31,32],run_program:[22,32],run_subtask:22,run_task:19,s:[9,15,18,22,24,28,32],same:[9,18,22,24,32],sampl:[0,2,8,9,10,12,13,15,16,18,22,24,25,27,28,32],sample_1:32,sample_2:32,sample_3:32,sample_4:32,sample_amount:15,sample_id:[13,17,18,24,32],sample_posit:[8,18,22,27,32],sample_position_prefix:18,sample_view:[0,8,27,30],samplebuild:[0,1,2,22],sampleposit:[8,17,18,27],samplepositionrequest:18,samplepositionslock:18,samplepositionstatu:18,sampleview:18,scan:10,schedul:32,script:7,search:[9,28],second:32,section:31,see:13,self:[7,8,22,24,27,32],semant:26,send:[5,22,32],sensor:[8,15],sent:[23,32],separ:17,serv:[31,32],server:5,session:7,set:[7,8,9,18,22,24,26,27,29,32],set_all_attribut:9,set_attribut:9,set_messag:[8,9,22,24],setdefault:7,setpoint:[22,32],setter:8,setup_lab:7,shall:9,sharabl:28,share:[22,28,32],should:[7,8,9,12,22,24,27,28,31,32],signal:[8,15],signal_nam:[8,15],signal_valu:[8,15],signal_value_1:8,signal_value_2:8,signifi:9,similar:32,simpli:28,simul:[22,32],sinc:28,singl:[8,18],skip:18,snippet:28,so:[7,8,9,22,24,26,27,28,32],some:[8,9,15,18,23,24,27,28,31],someth:28,soon:29,sort:7,sourc:[2,3,4,5,7,8,9,10,12,13,15,17,18,19,22,23,24,25,27,32],specif:9,specifi:[8,9,18,27,28,31],start:[5,7,8,10,23,24,28],startwith:18,state:9,statu:[5,9,13,18,19,23,24,25],step:32,still:[9,28],stop:[7,8,23,27,28],store:[7,8,9,24,27,31],str:[2,3,5,7,8,9,13,15,17,18,22,24,25,27,32],string:[15,17,25],structur:[5,18],subclass:[7,8,22,32],submit:[10,13,23,28],submodul:30,subpackag:30,subtask:[22,24],subtask_id:24,subtask_typ:24,success:5,support:8,supported_sample_posit:22,sure:26,sync:9,sync_device_statu:9,synthesi:28,system:[9,15,23,25,27,28,31,32],system_log:15,t:[8,27],take:[2,15,22,32],target:31,task:[0,2,3,5,9,10,12,13,15,17,18,19,21,23,24,25,29,31],task_1:31,task_2:31,task_3:31,task_actor:[0,30],task_entri:24,task_enum:[0,21],task_id:[2,3,5,9,13,15,17,18,22,24,25,32],task_kwarg:2,task_manag:[0,19,30],task_nam:2,task_result:24,task_typ:24,task_view:[0,30],tasklist:22,taskmanag:9,taskprior:[22,23,32],taskstatu:[23,24],taskview:24,tell:18,temperatur:[8,15,22,28,32],temporari:[8,27],test:26,than:15,them:[8,27,28,31],thi:[2,4,5,7,8,9,10,12,13,15,17,18,22,24,25,27,28,29,31,32],thing:[6,11,16,21],through:[25,28],throughout:28,time:[7,8,10,15,27],timedelta:[8,15],timeout:5,timestamp:[8,15],timestamp_1:8,timestamp_2:8,to_dict:[2,3],toml:31,too:[22,32],track:[8,26,28],trai:18,transfer:[8,27],translat:24,try_to_mark_task_readi:24,tupl:[18,32],two:[28,32],txt:[26,29],type:[2,3,4,5,7,8,9,13,15,17,18,22,24,25,26,27,32],type_or_nam:9,typic:9,uid:18,under:[7,8,28],union:[15,18,22,24],uniqu:[2,8,9,17,27],unit:26,unknown:9,unlock:18,unoccupi:18,unpaus:9,unpause_devic:9,until:[7,18,22,24,25,32],up:[8,9,26,27,29],updat:[7,13,18,19,24,25,28],update_experiment_statu:13,update_request_statu:25,update_result:24,update_sample_task_id:[13,18],update_statu:24,update_subtask_result:24,update_subtask_statu:24,update_task_depend:24,urgent:23,us:[2,5,7,8,9,13,18,19,22,24,26,27,28,31,32],usabl:9,usag:7,user:[8,9,12,13,23,25,27,28],user_input:[0,30],userinputview:25,usernam:[4,31],userrequeststatu:25,usual:[9,31],valid:[18,22,32],valu:[5,7,8,9,13,15,18,22,23,25,28,32],value_in_databas:7,valueerror:[7,9,18],variabl:[7,8],vertex:28,via:[5,26,28],view:[9,13,18,24,25,28],voltag:15,vs:8,wa:8,wait:[23,28],want:26,warn:15,we:[8,9,13,15,18,22,24,26,27,28,29,31,32],websit:28,weight:15,well:[9,28],what:28,when:[7,8,9,10,18,19,22,27,28,32],whenev:8,where:[8,15,27,31],whether:[8,9,18,24],which:[4,5,7,8,9,13,15,17,18,22,24,25,27,28,31,32],within:[2,7,8,15,18,24,32],work:[7,28,31],worker:19,workflow:[15,28,32],working_dir:[4,31],wrap:5,wrapper:[5,9,13,18,24,28],write:[12,27],wrong:19,wrote:15,x:7,xrd:15,yaml:4,yarn:26,yet:23,you:[18,22,26,27,28,29,31,32],your:[27,31]},titles:["alab_management package","alab_management.builders package","alab_management.builders.experimentbuilder module","alab_management.builders.samplebuilder module","alab_management.config module","alab_management.device_manager module","alab_management.device_view package","alab_management.device_view.dbattributes module","alab_management.device_view.device module","alab_management.device_view.device_view module","alab_management.experiment_manager module","alab_management.experiment_view package","alab_management.experiment_view.experiment module","alab_management.experiment_view.experiment_view module","alab_management.lab_view module","alab_management.logger module","alab_management.sample_view package","alab_management.sample_view.sample module","alab_management.sample_view.sample_view module","alab_management.task_actor module","alab_management.task_manager module","alab_management.task_view package","alab_management.task_view.task module","alab_management.task_view.task_enums module","alab_management.task_view.task_view module","alab_management.user_input module","Development","Defining a new device","Overview","Installation","alab_management","Set up definition folder","Defining a new task"],titleterms:{"new":[27,32],actor:28,alab_manag:[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,30],builder:[1,2,3],ci:26,code:29,command:31,commit:26,config:4,configur:31,content:[0,1,6,11,16,21],data:28,dbattribut:7,defin:[27,32],definit:31,develop:26,devic:[8,27],device_manag:5,device_view:[6,7,8,9],environ:26,experi:[12,28],experiment_manag:10,experiment_view:[11,12,13],experimentbuild:2,file:31,folder:31,from:29,git:26,indic:28,initi:31,instal:29,lab:28,lab_view:14,line:31,logger:15,manag:28,modul:[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,28],next:[29,31],overview:28,packag:[0,1,6,11,16,21],pip:29,prerequisit:29,project:31,rule:26,s:[29,31],sampl:17,sample_view:[16,17,18],samplebuild:3,set:31,setup:26,sourc:29,statu:28,storag:28,structur:31,submodul:[0,1,6,11,16,21],subpackag:0,system:26,tabl:28,task:[22,28,32],task_actor:19,task_enum:23,task_manag:20,task_view:[21,22,23,24],terminolog:28,up:31,user_input:25,via:[29,31],what:[29,31]}})