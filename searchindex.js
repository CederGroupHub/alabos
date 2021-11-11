Search.setIndex({docnames:["alab_management","alab_management.dashboard","alab_management.dashboard.routes","alab_management.device_view","alab_management.experiment_view","alab_management.sample_view","alab_management.scripts","alab_management.task_view","alab_management.utils","device_definition","index","installation","modules","setup","task_definition"],envversion:{"sphinx.domains.c":2,"sphinx.domains.changeset":1,"sphinx.domains.citation":1,"sphinx.domains.cpp":3,"sphinx.domains.index":1,"sphinx.domains.javascript":2,"sphinx.domains.math":2,"sphinx.domains.python":2,"sphinx.domains.rst":2,"sphinx.domains.std":1,"sphinx.ext.intersphinx":1,"sphinx.ext.todo":2,"sphinx.ext.viewcode":1,sphinx:56},filenames:["alab_management.rst","alab_management.dashboard.rst","alab_management.dashboard.routes.rst","alab_management.device_view.rst","alab_management.experiment_view.rst","alab_management.sample_view.rst","alab_management.scripts.rst","alab_management.task_view.rst","alab_management.utils.rst","device_definition.rst","index.rst","installation.rst","modules.rst","setup.rst","task_definition.rst"],objects:{"":{alab_management:[0,0,0,"-"]},"alab_management.config":{AlabConfig:[0,1,1,""],froze_config:[0,3,1,""]},"alab_management.config.AlabConfig":{path:[0,2,1,""]},"alab_management.dashboard":{create_app:[1,3,1,""]},"alab_management.db":{get_collection:[0,3,1,""]},"alab_management.device_view":{device:[3,0,0,"-"],device_view:[3,0,0,"-"]},"alab_management.device_view.device":{BaseDevice:[9,1,1,""],SamplePosition:[3,1,1,""],add_device:[3,3,1,""],get_all_devices:[3,3,1,""]},"alab_management.device_view.device.BaseDevice":{__init__:[9,2,1,""],description:[3,4,1,""],emergent_stop:[9,2,1,""],sample_positions:[9,2,1,""]},"alab_management.device_view.device.SamplePosition":{description:[3,4,1,""],name:[3,4,1,""]},"alab_management.device_view.device_view":{DeviceStatus:[3,1,1,""],DeviceView:[3,1,1,""],DevicesLock:[3,1,1,""]},"alab_management.device_view.device_view.DeviceStatus":{IDLE:[3,4,1,""],OCCUPIED:[3,4,1,""],UNKNOWN:[3,4,1,""]},"alab_management.device_view.device_view.DeviceView":{add_devices_to_db:[3,2,1,""],clean_up_device_collection:[3,2,1,""],get_device:[3,2,1,""],get_device_by_type:[3,2,1,""],get_status:[3,2,1,""],occupy_device:[3,2,1,""],release_device:[3,2,1,""],request_devices:[3,2,1,""]},"alab_management.device_view.device_view.DevicesLock":{devices:[3,2,1,""],release:[3,2,1,""]},"alab_management.executor":{Executor:[0,1,1,""],ParameterError:[0,5,1,""]},"alab_management.executor.Executor":{run:[0,2,1,""],submit_task:[0,2,1,""]},"alab_management.experiment_manager":{ExperimentManager:[0,1,1,""]},"alab_management.experiment_manager.ExperimentManager":{handle_pending_experiments:[0,2,1,""],mark_completed_experiments:[0,2,1,""],run:[0,2,1,""]},"alab_management.experiment_view":{experiment:[4,0,0,"-"],experiment_view:[4,0,0,"-"]},"alab_management.experiment_view.experiment":{InputExperiment:[4,1,1,""]},"alab_management.experiment_view.experiment.InputExperiment":{name:[4,4,1,""],samples:[4,4,1,""],tasks:[4,4,1,""]},"alab_management.experiment_view.experiment_view":{ExperimentStatus:[4,1,1,""],ExperimentView:[4,1,1,""]},"alab_management.experiment_view.experiment_view.ExperimentStatus":{COMPLETED:[4,4,1,""],PENDING:[4,4,1,""],RUNNING:[4,4,1,""]},"alab_management.experiment_view.experiment_view.ExperimentView":{create_experiment:[4,2,1,""],get_experiment:[4,2,1,""],get_experiments_with_status:[4,2,1,""],set_experiment_status:[4,2,1,""],update_sample_task_id:[4,2,1,""]},"alab_management.lab_manager":{LabManager:[0,1,1,""],resource_lock:[0,3,1,""]},"alab_management.lab_manager.LabManager":{get_sample:[0,2,1,""],move_sample:[0,2,1,""],request_devices:[0,2,1,""],request_resources:[0,2,1,""],request_sample_positions:[0,2,1,""]},"alab_management.logger":{DBLogger:[0,1,1,""],LoggingLevel:[0,1,1,""],LoggingType:[0,1,1,""]},"alab_management.logger.DBLogger":{filter_log:[0,2,1,""],log:[0,2,1,""],log_amount:[0,2,1,""],log_characterization_result:[0,2,1,""],log_device_signal:[0,2,1,""],system_log:[0,2,1,""]},"alab_management.logger.LoggingLevel":{CRITICAL:[0,4,1,""],DEBUG:[0,4,1,""],ERROR:[0,4,1,""],FATAL:[0,4,1,""],INFO:[0,4,1,""],WARN:[0,4,1,""],WARNING:[0,4,1,""]},"alab_management.logger.LoggingType":{CHARACTERIZATION_RESULT:[0,4,1,""],DEVICE_SIGNAL:[0,4,1,""],OTHER:[0,4,1,""],SAMPLE_AMOUNT:[0,4,1,""],SYSTEM_LOG:[0,4,1,""]},"alab_management.sample_view":{sample:[5,0,0,"-"],sample_view:[5,0,0,"-"]},"alab_management.sample_view.sample":{Sample:[5,1,1,""]},"alab_management.sample_view.sample.Sample":{name:[5,4,1,""],position:[5,4,1,""]},"alab_management.sample_view.sample_view":{SamplePositionStatus:[5,1,1,""],SamplePositionsLock:[5,1,1,""],SampleView:[5,1,1,""]},"alab_management.sample_view.sample_view.SamplePositionStatus":{EMPTY:[5,4,1,""],LOCKED:[5,4,1,""],OCCUPIED:[5,4,1,""]},"alab_management.sample_view.sample_view.SamplePositionsLock":{release:[5,2,1,""],sample_positions:[5,2,1,""]},"alab_management.sample_view.sample_view.SampleView":{add_sample_positions_to_db:[5,2,1,""],clean_up_sample_position_collection:[5,2,1,""],create_sample:[5,2,1,""],get_available_sample_position:[5,2,1,""],get_sample:[5,2,1,""],get_sample_position:[5,2,1,""],get_sample_position_status:[5,2,1,""],is_empty_position:[5,2,1,""],lock_sample_position:[5,2,1,""],move_sample:[5,2,1,""],release_sample_position:[5,2,1,""],request_sample_positions:[5,2,1,""],update_sample_task_id:[5,2,1,""]},"alab_management.scripts":{cleanup_lab:[6,0,0,"-"],launch_lab:[6,0,0,"-"],setup_lab:[6,0,0,"-"]},"alab_management.scripts.cleanup_lab":{cleanup_lab:[6,3,1,""]},"alab_management.scripts.launch_lab":{launch_executor:[6,3,1,""],launch_lab:[6,3,1,""],launch_task_manager:[6,3,1,""]},"alab_management.scripts.setup_lab":{setup_from_device_def:[6,3,1,""],setup_lab:[6,3,1,""]},"alab_management.task_view":{task:[7,0,0,"-"],task_view:[7,0,0,"-"]},"alab_management.task_view.task":{BaseTask:[14,1,1,""],add_task:[7,3,1,""],get_all_tasks:[7,3,1,""]},"alab_management.task_view.task.BaseTask":{__init__:[14,2,1,""],run:[14,2,1,""]},"alab_management.task_view.task_view":{TaskStatus:[7,1,1,""],TaskView:[7,1,1,""]},"alab_management.task_view.task_view.TaskStatus":{COMPLETED:[7,4,1,""],ERROR:[7,4,1,""],PAUSED:[7,4,1,""],READY:[7,4,1,""],RUNNING:[7,4,1,""],WAITING:[7,4,1,""]},"alab_management.task_view.task_view.TaskView":{create_task:[7,2,1,""],get_ready_tasks:[7,2,1,""],get_status:[7,2,1,""],get_task:[7,2,1,""],try_to_mark_task_ready:[7,2,1,""],update_status:[7,2,1,""],update_task_dependency:[7,2,1,""]},"alab_management.utils":{graph_op:[8,0,0,"-"],module_ops:[8,0,0,"-"]},"alab_management.utils.graph_op":{Graph:[8,1,1,""]},"alab_management.utils.graph_op.Graph":{get_children:[8,2,1,""],get_parents:[8,2,1,""],has_cycle:[8,2,1,""]},"alab_management.utils.module_ops":{import_module_from_path:[8,3,1,""],load_definition:[8,3,1,""]},alab_management:{config:[0,0,0,"-"],dashboard:[1,0,0,"-"],db:[0,0,0,"-"],device_view:[3,0,0,"-"],executor:[0,0,0,"-"],experiment_manager:[0,0,0,"-"],experiment_view:[4,0,0,"-"],lab_manager:[0,0,0,"-"],logger:[0,0,0,"-"],sample_view:[5,0,0,"-"],scripts:[6,0,0,"-"],task_view:[7,0,0,"-"],utils:[8,0,0,"-"]}},objnames:{"0":["py","module","Python module"],"1":["py","class","Python class"],"2":["py","method","Python method"],"3":["py","function","Python function"],"4":["py","attribute","Python attribute"],"5":["py","exception","Python exception"]},objtypes:{"0":"py:module","1":"py:class","2":"py:method","3":"py:function","4":"py:attribute","5":"py:exception"},terms:{"127":9,"27017":13,"502":9,"abstract":[3,7,9,10,14],"case":0,"class":[0,3,4,5,7,8,9,10,14],"default":13,"enum":[0,3,4,5,7],"float":14,"function":[3,7,9,14],"import":[6,8,9,10,14],"int":[3,9],"long":[9,14],"new":[5,7],"return":[0,3,4,5,7,8,9,14],"super":[9,14],"true":3,"try":[0,7,14],"while":[7,14],But:[9,14],DFS:8,For:[9,13],ROS:10,The:[0,3,4,6,7,9,10,13,14],There:3,Use:8,With:10,__init__:[9,13,14],_id:5,_sampl:4,_task:4,abc:[3,7],about:[3,7,9,14],access:11,accord:13,acquir:0,actual:0,acycl:10,add:[0,7],add_devic:[3,9],add_devices_to_db:3,add_sample_positions_to_db:5,add_task:[7,14],address:9,adjac:8,aim:10,alab:[10,13],alab_manag:[9,14],alabconfig:0,algorithm:8,all:[0,3,6,7,9,10,14],alloc:[7,14],allow:[0,10],alreadi:[3,5],also:[3,7,10,13,14],alwai:[9,14],ani:[0,3,4,5,7,8,9,14],api:3,appear:[3,5],architectur:10,arg:[9,14],assign:[4,7,10,13,14],attribut:[3,9],authent:[0,13],automat:[3,7,13,14],autonom:10,avail:[3,7,14],base:[0,3,4,5,7,8],basedevic:[3,9,10],basemodel:4,basetask:[7,10,14],basic:[5,10],batch:10,been:[4,5],befor:[7,13],besid:13,between:10,block:3,bool:[3,5,8],briefli:3,call:[7,14],can:[3,5,7,9,10,13,14],cannot:[7,14],certain:10,characterization_result:0,charg:0,check:[5,7],chemic:10,classvar:3,clean:3,clean_up_device_collect:3,clean_up_sample_position_collect:5,cleanup:6,cleanup_lab:[0,12],code:[9,10,14],collect:[0,3,4,5,6,7,10],command:[7,14],commun:10,complet:[0,4,7,10,14],conduct:10,config:[6,8,12,13],config_:0,configur:10,conflict:[7,14],connect:[9,13],construct:10,contain:10,content:12,context:[3,7,14],conveni:0,convert:0,coordin:[3,9],core:[0,6],creat:[4,5,10],create_app:1,create_experi:4,create_sampl:5,create_task:7,creation:4,critic:0,current:[5,7,10,14],custom:[0,9,11,13,14],cycl:[8,10],dag:10,dashboard:[0,12],data:[0,4,7,14],databas:[0,3,4,5,6,7,10,11,13,14],dblogger:[0,14],debug:0,def:[3,9,14],defin:[3,5,6,7,10,13],definit:[3,6,8,10,11],depend:10,describ:[3,9,10],descript:[3,5,9],dest:[7,14],detect:8,devic:[0,6,7,8,10,11,12,13,14],device_1:13,device_2:13,device_3:13,device_dir:6,device_nam:3,device_sign:0,device_typ:[0,3],device_view:[0,12],devicelock:3,devices_and_posit:[7,14],devices_and_sample_posit:0,devices_lock:0,deviceslock:[0,3],devicestatu:3,deviceview:[3,10],dict:[0,3,4,5,7],dir:[9,13,14],direct:10,directori:13,discuss:11,doe:[3,9],doesn:[3,9,14],done:10,driver:[9,10],drop:[5,6],duplic:3,dure:[0,7],each:[0,10],easier:6,easili:10,edg:8,els:5,emerg:[3,9],emergent_stop:[3,9],empti:[5,10],encount:7,entri:[5,7],enumer:[0,5],error:[0,7],exampl:[3,7,9,13,14],except:0,execut:[0,7,9,14],executor:[6,12],exist:5,exp_id:4,experi:[0,1,12],experiment_manag:12,experiment_view:[0,12],experimentmanag:0,experimentstatu:4,experimentview:4,extens:10,fatal:0,file:[6,8],filter:4,filter_log:0,find:0,finish:7,flexibl:10,folder:11,follow:4,format:[4,10],from:[3,6,7,8,9,10,14],froze_config:0,frozen:0,frozen_config:0,furnac:[3,7,9,14],furnace_1:9,furnace_t:[3,9],furnacecontrol:9,gener:[6,13],geograph:3,get:[0,3,4,5,7,14],get_all_devic:3,get_all_task:7,get_available_sample_posit:5,get_children:8,get_collect:0,get_devic:3,get_device_by_typ:3,get_experi:4,get_experiments_with_statu:4,get_par:8,get_ready_task:7,get_sampl:[0,5],get_sample_posit:5,get_sample_position_statu:5,get_statu:[3,7],get_task:7,get_temperatur:[7,14],git:10,github:10,given:3,going:3,graph:[8,10],graph_op:[0,12],great:10,handl:[7,13],handle_pending_experi:0,has:[3,4,5,7,10,13,14],has_cycl:8,have:[3,10,11],heat:[3,9,10,14],here:[3,7,9,14],hold:[3,7,9,10],host:[10,13],how:[3,7,9,11,13,14],identifi:[3,9,14],idl:[3,10],ids:[7,10],implement:10,import_module_from_path:8,includ:[3,5,9],independ:0,index:10,info:[0,5,7],inform:[0,3,9,10,14],inherit:[3,7,9,10,14],initi:[5,9],inputexperi:4,insert:[3,5,7],insid:[3,7,9,14],inside_furnac:[7,14],instanc:[3,5,10],introduc:13,is_empty_posit:5,is_run:[7,14],iter:0,its:[4,5,7,8,10],itself:13,just:[5,10,13],kind:9,kwarg:[9,14],lab:[3,5,7,9,13,14],lab_manag:[7,12,14],labmanag:[0,10,14],later:4,launch:6,launch_executor:6,launch_lab:[0,12],launch_task_manag:6,least:11,level:0,life:10,like:[10,13],list:[3,4,5,7,8,9,10,14],load:[8,9,13,14],load_definit:8,local:11,localhost:13,lock:[5,10],lock_sample_posit:5,log:[0,7,14],log_amount:0,log_characterization_result:0,log_data:0,log_device_sign:[0,7,14],logger:[7,12,14],logging_typ:0,logginglevel:0,loggingtyp:0,longer:3,look:13,mai:[10,13],main:4,make:[6,9,14],manag:[3,4,5,7,13,14],manual:[3,9],map:[3,9],mappingproxi:0,mark:[0,7],mark_completed_experi:0,matter:[3,9,14],maximum:3,mean:5,meet:3,method:[0,4,9],model:[0,12],modifi:0,modul:[12,13],module_op:[0,12],mongocli:0,mongodb:[6,10,11],more:[3,9,13,14],move:[7,14],move_sampl:[0,5],moving_task:[7,14],multipl:10,must:[7,10,11],name:[0,3,4,5,7,9,13,14],nameerror:3,need:[0,3,9,10,13,14],next:7,next_task:7,none:[3,5,7],now:7,number:[7,14],object:[0,3,4,5,7,8,9],objectid:[3,4,5,7,14],occupi:[3,5,10],occupy_devic:3,okai:13,old:7,onc:9,one:[3,5,7,11],ones:3,onli:[3,9],only_idl:3,oper:10,option:[3,4,5,7,14],other:[0,7,14],our:10,out:0,outsid:3,over:[7,10,14],overwrit:7,ownership:[3,7,14],packag:[10,12,13],page:10,param:4,paramet:[0,3,5,7,9,10,14],parametererror:0,parent:7,pass:7,password:13,path:[0,6,8],pattern:0,paus:7,pend:[0,4,7,10,14],place:10,platform:10,pleas:[9,13],port:[9,13],posit:[0,3,5,6,7,9,10,14],position_prefix:5,pre_task:7,predefin:[0,10],prev:7,prev_task:7,prevent:[7,14],previou:[7,10],procedur:0,process:[0,4],project:10,project_root:13,properli:[9,14],properti:[0,3,5,9],provid:[3,9,10,13,14],put:[4,10],pydant:4,pymongo:10,python:[10,11,13],queri:6,queue:4,rack:10,rais:[0,3],reach:[9,14],read:10,readi:[0,3,7,10],real:[3,9,10],recommend:[9,14],record:[0,10,14],refer:[7,9,10,11,13,14],regist:[3,7,13],registri:[3,7],releas:[3,5,7,14],release_devic:3,release_sample_posit:5,remot:11,remov:6,renew:9,repo:[9,13],repositori:10,repres:[7,10,14],represent:10,request:[3,7,10,14],request_devic:[0,3],request_resourc:[0,7,14],request_sample_posit:[0,5],requir:[3,7,10],resourc:[7,10,13,14],resource_lock:0,robot:10,robot_arm:3,robotarm:3,root:[9,14],rout:[0,1],run:[0,4,7,10,13,14],run_program:[7,14],same:[3,5,7,14],sampl:[0,3,4,6,7,9,10,12,14],sample_1:14,sample_2:14,sample_3:14,sample_4:14,sample_amount:0,sample_id:[0,4,5],sample_posit:[0,3,5,6,7,9,14],sample_positions_lock:0,sample_view:[0,12],sampleposit:[3,9],samplepositionslock:[0,5],samplepositionstatu:5,sampleview:[5,10],scan:0,script:[0,12],search:10,second:3,section:13,see:3,self:[3,7,9,14],send:[7,14],serv:13,set:[3,6,9,11],set_experiment_statu:4,setpoint:[7,14],setup:11,setup_from_device_def:6,setup_lab:[0,12],shall:3,sharabl:10,share:[7,10,14],should:[3,4,7,9,10,13,14],similar:14,sinc:10,skip:5,snippet:10,some:[0,3,5,7,9,10,13],someth:[3,10],sourc:[0,1,3,4,5,6,7,8,9,14],specifi:[3,6,8,9,10,13],start:7,statu:[3,4,5,7],still:10,stop:[3,9,10],store:[0,3,7,8,9,13],str:[0,3,4,5,7,9],string:3,structur:13,submit:[0,4,7,10],submit_task:0,submodul:12,subpackag:12,sure:[9,14],synthesi:10,system:[0,6,9,10,13,14],system_log:0,tabl:8,take:[0,7,14],task:[0,3,4,5,6,8,10,11,12,13],task_1:13,task_2:13,task_3:13,task_entri:0,task_id:[0,3,4,5,7,14],task_typ:7,task_view:[0,6,12],taskstatu:7,taskview:7,tell:5,temperatur:[7,10,14],temporari:[3,9],than:3,them:[0,3,6,9,10,13],thi:[0,3,4,5,7,9,10,11,13,14],thread:0,three:10,throughout:10,time:[0,9],timeout:[0,3,5],toml:13,track:10,transfer:[3,9],try_to_mark_task_readi:7,tupl:[5,14],two:10,type:[0,3,4,5,7,8,9],uid:5,under:10,union:7,uniqu:[3,5,9],unknown:3,unlock:5,until:[3,7,14],updat:[4,5,7,10,14],update_sample_task_id:[4,5],update_statu:7,update_task_depend:7,use:[3,4,7,9,10,13,14],used:[0,10],user:[3,4,6,9,10],usernam:13,usual:13,util:[0,12],valid:5,valu:[0,3,4,5,7,10],valueerror:3,vertex:10,vertic:8,via:10,view:[3,4,5,7,10,14],wait:[3,7,10],want:14,warn:0,websit:10,well:[3,10],what:10,when:[0,3,7,9,10,14],where:[0,3,9,13,14],which:[0,3,4,5,6,7,9,10,13,14],whose:6,within:0,work:[10,13],workflow:10,working_dir:13,wrapper:[0,10],write:[4,6,9],wrong:0,wrote:0,you:[3,7,9,10,11,13,14],your:[9,13]},titles:["alab_management package","alab_management.dashboard package","alab_management.dashboard.routes package","alab_management.device_view package","alab_management.experiment_view package","alab_management.sample_view package","alab_management.scripts package","alab_management.task_view package","alab_management.utils package","Defining a new device","Overview","Installation","alab_management","Set up definition folder","Defining a new task"],titleterms:{"new":[9,14],For:11,alab_manag:[0,1,2,3,4,5,6,7,8,12],cleanup_lab:6,config:0,configur:13,content:[0,1,2,3,4,5,6,7,8],dashboard:[1,2],data:10,defin:[9,14],definit:13,develop:11,devic:[3,9],device_view:3,executor:[0,10],experi:[2,4,10],experiment_manag:0,experiment_view:4,file:13,folder:13,graph_op:8,indic:10,instal:11,lab:10,lab_manag:0,launch_lab:6,logger:0,manag:10,model:1,modul:[0,1,2,3,4,5,6,7,8,10],module_op:8,next:[11,13],overview:10,packag:[0,1,2,3,4,5,6,7,8],prerequisit:11,purpos:11,regist:[9,14],rout:2,sampl:5,sample_view:5,script:6,set:13,setup_lab:6,statu:10,storag:10,submodul:[0,1,2,3,4,5,6,7,8],subpackag:[0,1],tabl:10,task:[7,14],task_view:7,terminolog:10,util:8,what:[11,13]}})