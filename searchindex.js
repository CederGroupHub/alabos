Search.setIndex({docnames:["alab_management","alab_management.config","alab_management.db","alab_management.device_view","alab_management.device_view.device","alab_management.device_view.device_view","alab_management.experiment_manager","alab_management.experiment_view","alab_management.experiment_view.experiment","alab_management.experiment_view.experiment_view","alab_management.lab_manager","alab_management.logger","alab_management.sample_view","alab_management.sample_view.sample","alab_management.sample_view.sample_view","alab_management.task_actor","alab_management.task_launcher","alab_management.task_view","alab_management.task_view.task","alab_management.task_view.task_view","device_definition","index","installation","modules","setup","task_definition"],envversion:{"sphinx.domains.c":2,"sphinx.domains.changeset":1,"sphinx.domains.citation":1,"sphinx.domains.cpp":3,"sphinx.domains.index":1,"sphinx.domains.javascript":2,"sphinx.domains.math":2,"sphinx.domains.python":2,"sphinx.domains.rst":2,"sphinx.domains.std":1,"sphinx.ext.intersphinx":1,"sphinx.ext.todo":2,"sphinx.ext.viewcode":1,sphinx:56},filenames:["alab_management.rst","alab_management.config.rst","alab_management.db.rst","alab_management.device_view.rst","alab_management.device_view.device.rst","alab_management.device_view.device_view.rst","alab_management.experiment_manager.rst","alab_management.experiment_view.rst","alab_management.experiment_view.experiment.rst","alab_management.experiment_view.experiment_view.rst","alab_management.lab_manager.rst","alab_management.logger.rst","alab_management.sample_view.rst","alab_management.sample_view.sample.rst","alab_management.sample_view.sample_view.rst","alab_management.task_actor.rst","alab_management.task_launcher.rst","alab_management.task_view.rst","alab_management.task_view.task.rst","alab_management.task_view.task_view.rst","device_definition.rst","index.rst","installation.rst","modules.rst","setup.rst","task_definition.rst"],objects:{"":{alab_management:[0,0,0,"-"]},"alab_management.config":{froze_config:[1,1,1,""]},"alab_management.db":{get_collection:[2,1,1,""],get_lock:[2,1,1,""]},"alab_management.device_view":{device:[4,0,0,"-"],device_view:[5,0,0,"-"]},"alab_management.device_view.device":{BaseDevice:[20,2,1,""],add_device:[4,1,1,""],get_all_devices:[4,1,1,""]},"alab_management.device_view.device.BaseDevice":{__init__:[20,3,1,""],description:[20,4,1,""],emergent_stop:[20,3,1,""],is_running:[4,3,1,""],sample_positions:[20,3,1,""]},"alab_management.device_view.device_view":{DeviceStatus:[5,2,1,""],DeviceView:[5,2,1,""],DevicesLock:[5,2,1,""]},"alab_management.device_view.device_view.DeviceStatus":{ERROR:[5,4,1,""],HOLD:[5,4,1,""],IDLE:[5,4,1,""],OCCUPIED:[5,4,1,""],UNKNOWN:[5,4,1,""]},"alab_management.device_view.device_view.DeviceView":{add_devices_to_db:[5,3,1,""],clean_up_device_collection:[5,3,1,""],get_all:[5,3,1,""],get_available_devices:[5,3,1,""],get_device:[5,3,1,""],get_devices_by_task:[5,3,1,""],get_status:[5,3,1,""],occupy_device:[5,3,1,""],release_device:[5,3,1,""],request_devices:[5,3,1,""],sync_device_status:[5,3,1,""]},"alab_management.device_view.device_view.DevicesLock":{devices:[5,3,1,""],release:[5,3,1,""],running_devices:[5,3,1,""]},"alab_management.experiment_manager":{ExperimentManager:[6,2,1,""]},"alab_management.experiment_manager.ExperimentManager":{handle_pending_experiments:[6,3,1,""],mark_completed_experiments:[6,3,1,""],run:[6,3,1,""]},"alab_management.experiment_view":{experiment:[8,0,0,"-"],experiment_view:[9,0,0,"-"]},"alab_management.experiment_view.experiment":{InputExperiment:[8,2,1,""]},"alab_management.experiment_view.experiment.InputExperiment":{name:[8,4,1,""],samples:[8,4,1,""],tasks:[8,4,1,""]},"alab_management.experiment_view.experiment_view":{ExperimentStatus:[9,2,1,""],ExperimentView:[9,2,1,""]},"alab_management.experiment_view.experiment_view.ExperimentStatus":{COMPLETED:[9,4,1,""],PENDING:[9,4,1,""],RUNNING:[9,4,1,""]},"alab_management.experiment_view.experiment_view.ExperimentView":{create_experiment:[9,3,1,""],get_experiment:[9,3,1,""],get_experiments_with_status:[9,3,1,""],update_experiment_status:[9,3,1,""],update_sample_task_id:[9,3,1,""]},"alab_management.lab_manager":{DeviceRunningException:[10,5,1,""],LabManager:[10,2,1,""],ResourcesRequest:[10,2,1,""]},"alab_management.lab_manager.LabManager":{get_locked_sample_positions:[10,3,1,""],get_occupied_devices:[10,3,1,""],get_sample:[10,3,1,""],move_sample:[10,3,1,""],request_resources:[10,3,1,""],task_id:[10,3,1,""]},"alab_management.lab_manager.ResourcesRequest":{preprocess:[10,3,1,""]},"alab_management.logger":{DBLogger:[11,2,1,""],LoggingLevel:[11,2,1,""],LoggingType:[11,2,1,""]},"alab_management.logger.DBLogger":{filter_log:[11,3,1,""],log:[11,3,1,""],log_amount:[11,3,1,""],log_characterization_result:[11,3,1,""],log_device_signal:[11,3,1,""],system_log:[11,3,1,""]},"alab_management.logger.LoggingLevel":{CRITICAL:[11,4,1,""],DEBUG:[11,4,1,""],ERROR:[11,4,1,""],FATAL:[11,4,1,""],INFO:[11,4,1,""],WARN:[11,4,1,""],WARNING:[11,4,1,""]},"alab_management.logger.LoggingType":{CHARACTERIZATION_RESULT:[11,4,1,""],DEVICE_SIGNAL:[11,4,1,""],OTHER:[11,4,1,""],SAMPLE_AMOUNT:[11,4,1,""],SYSTEM_LOG:[11,4,1,""]},"alab_management.sample_view":{sample:[13,0,0,"-"],sample_view:[14,0,0,"-"]},"alab_management.sample_view.sample":{Sample:[13,2,1,""],SamplePosition:[13,2,1,""]},"alab_management.sample_view.sample.Sample":{name:[13,4,1,""],position:[13,4,1,""],task_id:[13,4,1,""]},"alab_management.sample_view.sample.SamplePosition":{SEPARATOR:[13,4,1,""],description:[13,4,1,""],name:[13,4,1,""],number:[13,4,1,""]},"alab_management.sample_view.sample_view":{SamplePositionRequest:[14,2,1,""],SamplePositionStatus:[14,2,1,""],SamplePositionsLock:[14,2,1,""],SampleView:[14,2,1,""]},"alab_management.sample_view.sample_view.SamplePositionRequest":{from_py_type:[14,3,1,""],from_str:[14,3,1,""],number:[14,4,1,""],prefix:[14,4,1,""]},"alab_management.sample_view.sample_view.SamplePositionStatus":{EMPTY:[14,4,1,""],LOCKED:[14,4,1,""],OCCUPIED:[14,4,1,""]},"alab_management.sample_view.sample_view.SamplePositionsLock":{release:[14,3,1,""],sample_positions:[14,3,1,""]},"alab_management.sample_view.sample_view.SampleView":{add_sample_positions_to_db:[14,3,1,""],clean_up_sample_position_collection:[14,3,1,""],create_sample:[14,3,1,""],get_available_sample_position:[14,3,1,""],get_sample:[14,3,1,""],get_sample_position:[14,3,1,""],get_sample_position_status:[14,3,1,""],get_sample_positions_by_task:[14,3,1,""],is_unoccupied_position:[14,3,1,""],lock_sample_position:[14,3,1,""],move_sample:[14,3,1,""],release_sample_position:[14,3,1,""],request_sample_positions:[14,3,1,""],update_sample_task_id:[14,3,1,""]},"alab_management.task_actor":{ParameterError:[15,5,1,""]},"alab_management.task_launcher":{TaskLauncher:[16,2,1,""]},"alab_management.task_launcher.TaskLauncher":{run:[16,3,1,""]},"alab_management.task_view":{task:[18,0,0,"-"],task_view:[19,0,0,"-"]},"alab_management.task_view.task":{BaseTask:[25,2,1,""],add_task:[18,1,1,""],get_all_tasks:[18,1,1,""]},"alab_management.task_view.task.BaseTask":{__init__:[25,3,1,""],run:[25,3,1,""]},"alab_management.task_view.task_view":{TaskStatus:[19,2,1,""],TaskView:[19,2,1,""]},"alab_management.task_view.task_view.TaskStatus":{COMPLETED:[19,4,1,""],ERROR:[19,4,1,""],PAUSED:[19,4,1,""],READY:[19,4,1,""],REQUESTING_RESOURCE:[19,4,1,""],RUNNING:[19,4,1,""],STOPPED:[19,4,1,""],WAITING:[19,4,1,""]},"alab_management.task_view.task_view.TaskView":{create_task:[19,3,1,""],encode_task:[19,3,1,""],get_ready_tasks:[19,3,1,""],get_status:[19,3,1,""],get_task:[19,3,1,""],try_to_mark_task_ready:[19,3,1,""],update_result:[19,3,1,""],update_status:[19,3,1,""],update_task_dependency:[19,3,1,""]},alab_management:{config:[1,0,0,"-"],db:[2,0,0,"-"],device_view:[3,0,0,"-"],experiment_manager:[6,0,0,"-"],experiment_view:[7,0,0,"-"],lab_manager:[10,0,0,"-"],logger:[11,0,0,"-"],sample_view:[12,0,0,"-"],task_actor:[15,0,0,"-"],task_launcher:[16,0,0,"-"],task_view:[17,0,0,"-"]}},objnames:{"0":["py","module","Python module"],"1":["py","function","Python function"],"2":["py","class","Python class"],"3":["py","method","Python method"],"4":["py","attribute","Python attribute"],"5":["py","exception","Python exception"]},objtypes:{"0":"py:module","1":"py:function","2":"py:class","3":"py:method","4":"py:attribute","5":"py:exception"},terms:{"127":20,"27017":24,"502":20,"abstract":[4,18,20,21,25],"case":2,"class":[4,5,6,8,9,10,11,13,14,16,18,19,20,21,25],"default":[14,24],"enum":[5,9,11,14,19],"float":25,"function":[5,11,14,18,20,25],"import":[20,21,25],"int":[5,10,11,13,14,20],"long":[20,25],"new":[10,14,19],"return":[1,2,4,5,9,10,11,14,18,19,20,25],"super":[20,25],"true":5,"try":[10,14,18,19,25],"while":[18,19,25],And:10,But:[20,25],For:[20,24],ROS:21,The:[4,5,9,10,14,15,18,19,20,21,24,25],There:5,With:21,__exit__:[5,14],__init__:[20,24,25],_devicetyp:5,_id:[13,19],_resource_lock:10,_sampl:8,_task:8,abc:[4,18],about:[4,18,20,25],access:[10,22],accord:24,actual:[14,16],acycl:21,add:[2,9,19],add_devic:[4,20],add_devices_to_db:5,add_sample_positions_to_db:14,add_task:[18,25],address:20,after:14,aim:21,alab:[21,24],alab_manag:[20,25],alabo:24,all:[4,5,10,14,16,18,19,20,21,25],alloc:[18,25],allow:[1,21],alreadi:[5,14],also:[5,9,10,18,19,21,24,25],alwai:[20,25],amount:11,ani:[4,5,6,9,10,11,14,19,20],api:5,appear:[5,14],architectur:21,arg:[20,25],assign:[9,10,18,19,21,24,25],attribut:[4,20],authent:[2,24],automat:[5,18,24,25],autonom:21,avail:[5,10,14,18,25],base:[4,5,6,8,9,10,11,13,14,15,16,18,19],basedevic:[4,5,10,20,21],basemodel:[8,10,14],basetask:[18,19,21,25],basic:[11,13,21],batch:21,batteri:11,been:[9,13],befor:[19,24],belong:10,besid:24,between:21,block:5,bool:[4,5,14,19],briefli:13,bson:13,call:[5,14,18,25],can:[4,5,10,11,13,14,18,19,20,21,24,25],cannot:[14,18,19,25],certain:[11,21],character:11,characterization_result:11,charg:11,check:[4,14,19],chemic:[11,21],classmethod:[10,14],classvar:[4,13],clean:5,clean_up_device_collect:5,clean_up_sample_position_collect:14,code:[20,21,25],collect:[2,5,6,9,14,19,21],come:11,command:[18,25],commun:21,complet:[6,9,18,19,21,25],conduct:21,config:[0,23,24],config_:1,configur:21,conflict:[18,25],connect:[20,24],constrainedintvalu:14,constrainedstrvalu:8,construct:21,contain:21,content:23,context:[5,14,18,25],conveni:2,convert:1,coordin:[4,13,20],core:16,correspond:19,creat:[9,14,21],create_experi:9,create_sampl:14,create_task:19,creation:9,critic:11,current:[13,18,19,21,25],custom:[11,20,22,24,25],cycl:21,dag:21,dashboard:5,data:[1,8,10,11,14,18,25],databas:[5,6,8,9,11,13,14,18,19,21,22,24,25],dblogger:11,debug:11,def:[4,20,25],defin:[4,13,14,18,21,24],definit:[5,21,22],depend:21,describ:[4,13,20,21],descript:[4,5,13,14,20],dest:[18,25],devic:[0,3,5,10,11,18,21,22,24,25],device_1:24,device_2:24,device_3:24,device_nam:5,device_name_1:5,device_sign:11,device_typ:5,device_view:[0,23],devicelock:5,devicerunningexcept:10,devices_and_posit:[18,25],devices_and_sample_posit:10,deviceslock:5,devicestatu:5,devicetyp:10,deviceview:[5,21],dict:[1,4,5,9,10,11,14,18,19],differ:11,dir:[20,24,25],direct:21,directli:14,directori:24,discuss:22,doe:[4,20],doesn:[4,20,25],done:[9,21],driver:[20,21],drop:14,dump:19,duplic:5,dure:[11,19],each:[10,21],easili:21,els:[11,14],emerg:[4,20],emergent_stop:[4,20],empti:[14,21,24],encod:19,encode_task:19,encount:19,entri:[5,14,19],error:[5,11,19],event:6,exampl:[4,18,20,24,25],except:[10,15],execut:[11,16,19,20,25],executor:6,exist:14,exit:14,exp_id:9,experi:[0,6,7,9],experiment_manag:[0,23],experiment_view:[0,23],experimentmanag:6,experimentstatu:9,experimentview:9,extens:21,fals:19,fatal:11,filter:9,filter_log:11,find:[6,10,11,16],finish:19,flag:6,flexibl:21,folder:22,follow:[8,24],format:[5,8,9,10,14,21],found:[5,19],from:[4,6,11,18,19,20,21,25],from_py_typ:14,from_str:14,froze_config:1,frozen:1,frozen_config:1,furnac:[4,5,10,11,18,20,25],furnace_1:[10,20],furnace_t:[4,20],furnacecontrol:20,gener:24,geograph:13,get:[2,4,5,9,10,14,18,19,25],get_al:5,get_all_devic:4,get_all_task:18,get_available_devic:5,get_available_sample_posit:14,get_collect:2,get_devic:5,get_devices_by_task:5,get_experi:9,get_experiments_with_statu:9,get_lock:2,get_locked_sample_posit:10,get_occupied_devic:10,get_ready_task:19,get_sampl:[10,14],get_sample_posit:14,get_sample_position_statu:14,get_sample_positions_by_task:14,get_statu:[5,19],get_task:19,get_temperatur:[18,25],git:21,github:21,given:[5,14],going:5,graph:21,great:21,handl:[19,24],handle_pending_experi:6,has:[5,9,10,13,14,18,21,24,25],have:[5,10,14,21,22],heat:[4,20,21,25],here:[4,5,18,20,25],higher:11,hold:[4,5,13,19,20,21],host:[21,24],how:[4,18,20,22,24,25],identifi:[4,5,13,20,25],idl:[5,21],ids:[19,21],implement:21,includ:[4,5,14,20],index:21,indic:[5,14],info:[11,14,19],inform:[4,11,20,21],inherit:[4,18,19,20,21,25],init:24,initi:[13,20],input:14,inputexperi:[8,9],insert:[5,9,14,19],insid:[4,10,18,20,25],inside_furnac:[18,25],instanc:[4,10,14,21],instead:10,intend:9,interest:19,introduc:24,is_run:[4,18,25],is_unoccupied_posit:14,iter:11,its:[5,9,14,19,21],itself:24,job:19,just:[14,21,24],kind:[4,20],know:10,kwarg:[20,25],lab:[4,9,13,18,20,24,25],lab_manag:[0,18,23,25],labmanag:[9,10,21],later:9,least:22,level:11,life:21,like:[21,24],list:[4,5,8,9,10,14,19,20,21,25],load:[20,24,25],local:22,localhost:24,lock:[14,21],lock_sample_posit:14,log:[11,18,25],log_amount:11,log_characterization_result:11,log_data:11,log_device_sign:[11,18,25],logger:[0,18,23,25],logging_typ:11,logginglevel:11,loggingtyp:11,longer:5,look:24,loop:[6,16],mai:[5,21,24],main:[8,10,14],make:[20,25],manag:[5,6,9,14,18,19,24,25],manual:[4,20],map:[4,20],mappingproxi:1,mark:[6,19],mark_completed_experi:6,match:14,matter:[4,20,25],maximum:5,mean:13,method:[5,6,9,14,19,20],modifi:1,modul:[23,24],mongocli:2,mongodb:[19,21,22],mongolock:2,more:[5,20,24],move:[10,18,25],move_sampl:[10,14],moving_task:[18,25],multipl:[10,21],must:[19,21,22,24],name:[2,4,5,8,10,13,14,18,19,20,24,25],nameerror:5,need:[2,4,5,14,20,21,24,25],need_releas:[5,14],neither:14,next:19,next_task:19,none:[5,10,13,14,19],nor:14,note:10,now:[5,19],number:[10,13,14,18,25],object:[5,6,9,10,11,13,14,16,19,20],objectid:[5,9,10,11,13,14,19,25],occupi:[5,10,14,21],occupy_devic:5,okai:24,old:19,onc:20,one:[5,10,14,19,22],ones:5,onli:[5,10,20,24],only_idl:5,oper:21,option:[5,9,13,14,19,25],other:[11,18,25],our:21,out:6,outsid:5,over:[10,18,21,25],overwrit:19,ownership:[5,18,25],packag:[21,23,24],page:21,param:11,paramet:[1,5,9,14,15,19,20,21,25],parametererror:15,parent:19,pars:10,pass:19,password:24,pattern:11,paus:19,pend:[6,9,18,21,25],place:21,platform:21,pleas:[20,24],port:[20,24],posit:[4,10,13,14,18,20,21,25],position_prefix:14,pre_task:19,predefin:[11,21],prefix:[10,14],preprocess:10,prev:19,prev_task:19,prevent:[18,25],previou:[19,21],princip:10,procedur:2,process:9,project:21,project_root:24,properli:[20,25],properti:[4,5,10,14,20],provid:[5,20,21,24,25],put:[9,10,21],pydant:[8,10,14],pymongo:21,python:[19,21,22,24],queri:10,queue:9,rack:21,rais:[5,10,15],rang:11,raw:9,reach:[20,25],read:[6,21],readi:[5,16,19,21],real:[4,20,21],recommend:[20,25],record:[11,21],refer:[19,20,21,22,24],regardless:[5,10],regist:[4,18,24],registri:[4,18],releas:[5,10,14,18,25],release_devic:5,release_sample_posit:14,remot:22,renam:19,renew:20,replac:10,repo:[20,24],repositori:21,repres:[10,18,21,25],represent:21,request:[5,10,14,18,21,25],request_devic:5,request_resourc:[10,18,25],request_sample_posit:14,requesting_resourc:19,requir:[9,19,21],reserv:14,resourc:[10,14,18,21,24,25],resource_request:10,resourcesrequest:10,result:[11,19],robot:21,robot_arm:5,robotarm:5,root:[20,25],run:[4,5,6,9,10,16,18,19,21,24,25],run_program:[18,25],running_devic:5,same:[5,10,14,18,19,25],sampl:[0,4,8,9,10,11,12,14,18,19,20,21,25],sample_1:25,sample_2:25,sample_3:25,sample_4:25,sample_amount:11,sample_id:[9,10,14],sample_posit:[4,14,18,20,25],sample_position_1:10,sample_position_prefix:14,sample_position_prefix_1:14,sample_view:[0,23],sampleposit:[4,13,14,20],samplepositionrequest:[10,14],samplepositionslock:14,samplepositionstatu:14,sampleview:[14,21],scan:6,search:21,second:[5,14],section:24,see:[5,9,10],self:[4,18,19,20,25],send:[18,25],sensor:11,separ:13,serv:24,set:[4,5,14,20,22],setpoint:[18,25],setup:22,shall:5,sharabl:21,share:[18,21,25],should:[4,5,8,10,14,18,19,20,21,24,25],signal:11,similar:25,sinc:[10,21],skip:14,snippet:21,some:[4,5,11,14,19,20,21,24],someth:[5,21],sometim:10,sourc:[1,4,5,6,8,9,10,11,13,14,15,16,18,19,20,25],specifi:[4,10,14,20,21,24],start:[6,10,16,19],startwith:14,statu:[5,9,10,14,19],still:[5,10,21],stop:[4,19,20,21],store:[4,19,20,24],str:[4,5,9,10,11,13,14,18,19,20],string:[11,13],structur:14,submit:[6,9,16,19,21],submodul:23,subpackag:23,sure:[20,25],sync:5,sync_device_statu:5,synthesi:21,system:[5,11,16,20,21,24,25],system_log:11,take:[11,18,25],target:24,task:[0,5,6,8,9,10,11,14,15,16,17,19,22,24],task_1:24,task_2:24,task_3:24,task_actor:[0,23],task_entri:19,task_id:[5,9,10,11,13,14,18,19,25],task_launch:[0,23],task_result:19,task_typ:19,task_view:[0,23],tasklaunch:16,taskstatu:19,taskview:19,tell:14,temperatur:[11,18,21,25],temporari:[4,20],than:[5,11],them:[4,16,20,21,24],thi:[4,5,6,8,9,10,11,13,14,18,19,20,21,22,24,25],three:21,throughout:21,time:[6,11,20],timeout:[5,14],toml:24,track:21,transfer:[4,20],translat:19,try_to_mark_task_readi:19,tupl:[14,25],two:21,type:[1,2,4,5,9,10,11,14,18,19,20],uid:14,under:[10,21],union:[11,14,19],uniqu:[4,5,13,20],unknown:5,unlock:14,unoccupi:14,until:[5,10,14,18,19,25],updat:[9,10,14,19,21],update_experiment_statu:9,update_result:19,update_sample_task_id:[9,14],update_statu:19,update_task_depend:19,usabl:5,use:[4,9,10,18,20,21,24,25],used:[5,10,14,21],user:[4,8,9,20,21],usernam:24,using:19,usual:[5,10,24],valid:[10,14],valu:[5,9,10,11,14,19,21],valueerror:5,vertex:21,via:21,view:[5,9,10,14,19,21],voltag:11,wait:[5,19,21],want:10,warn:11,websit:21,weight:11,well:[5,21],what:21,when:[4,5,10,14,15,18,20,21,25],where:[4,11,20,24,25],whether:[4,5,14,19],which:[1,4,5,9,10,11,13,14,16,18,19,20,21,24,25],within:11,work:[21,24],workflow:[11,21],working_dir:24,wrapper:[2,10,21],write:[8,20],wrong:15,wrote:11,xrd:11,you:[5,10,14,18,20,21,22,24,25],your:[20,24]},titles:["alab_management package","alab_management.config module","alab_management.db module","alab_management.device_view package","alab_management.device_view.device module","alab_management.device_view.device_view module","alab_management.experiment_manager module","alab_management.experiment_view package","alab_management.experiment_view.experiment module","alab_management.experiment_view.experiment_view module","alab_management.lab_manager module","alab_management.logger module","alab_management.sample_view package","alab_management.sample_view.sample module","alab_management.sample_view.sample_view module","alab_management.task_actor module","alab_management.task_launcher module","alab_management.task_view package","alab_management.task_view.task module","alab_management.task_view.task_view module","Defining a new device","Overview","Installation","alab_management","Set up definition folder","Defining a new task"],titleterms:{"new":[20,25],For:22,alab_manag:[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,23],command:24,config:1,configur:24,content:[0,3,7,12,17],data:21,defin:[20,25],definit:24,develop:22,devic:[4,20],device_view:[3,4,5],experi:[8,21],experiment_manag:6,experiment_view:[7,8,9],file:24,folder:24,indic:21,initi:24,instal:22,lab:21,lab_manag:10,launcher:21,line:24,logger:11,manag:21,modul:[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,21],next:[22,24],overview:21,packag:[0,3,7,12,17],prerequisit:22,project:24,purpos:22,regist:[20,25],sampl:13,sample_view:[12,13,14],set:24,statu:21,storag:21,structur:24,submodul:[0,3,7,12,17],subpackag:0,tabl:21,task:[18,21,25],task_actor:15,task_launch:16,task_view:[17,18,19],terminolog:21,via:24,what:[22,24]}})