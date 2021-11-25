Search.setIndex({docnames:["alab_management","alab_management.device_view","alab_management.experiment_view","alab_management.sample_view","alab_management.task_view","device_definition","index","installation","modules","setup","task_definition"],envversion:{"sphinx.domains.c":2,"sphinx.domains.changeset":1,"sphinx.domains.citation":1,"sphinx.domains.cpp":3,"sphinx.domains.index":1,"sphinx.domains.javascript":2,"sphinx.domains.math":2,"sphinx.domains.python":2,"sphinx.domains.rst":2,"sphinx.domains.std":1,"sphinx.ext.intersphinx":1,"sphinx.ext.todo":2,"sphinx.ext.viewcode":1,sphinx:56},filenames:["alab_management.rst","alab_management.device_view.rst","alab_management.experiment_view.rst","alab_management.sample_view.rst","alab_management.task_view.rst","device_definition.rst","index.rst","installation.rst","modules.rst","setup.rst","task_definition.rst"],objects:{"":{alab_management:[0,0,0,"-"]},"alab_management.config":{AlabConfig:[0,1,1,""],froze_config:[0,3,1,""]},"alab_management.config.AlabConfig":{path:[0,2,1,""]},"alab_management.db":{get_collection:[0,3,1,""]},"alab_management.device_view":{device:[1,0,0,"-"],device_view:[1,0,0,"-"]},"alab_management.device_view.device":{BaseDevice:[5,1,1,""],add_device:[1,3,1,""],get_all_devices:[1,3,1,""]},"alab_management.device_view.device.BaseDevice":{__init__:[5,2,1,""],description:[1,4,1,""],emergent_stop:[5,2,1,""],is_running:[1,2,1,""],sample_positions:[5,2,1,""]},"alab_management.device_view.device_view":{DeviceStatus:[1,1,1,""],DeviceView:[1,1,1,""],DevicesLock:[1,1,1,""]},"alab_management.device_view.device_view.DeviceStatus":{ERROR:[1,4,1,""],HOLD:[1,4,1,""],IDLE:[1,4,1,""],OCCUPIED:[1,4,1,""],UNKNOWN:[1,4,1,""]},"alab_management.device_view.device_view.DeviceView":{add_devices_to_db:[1,2,1,""],clean_up_device_collection:[1,2,1,""],get_all:[1,2,1,""],get_available_devices:[1,2,1,""],get_device:[1,2,1,""],get_status:[1,2,1,""],occupy_device:[1,2,1,""],release_device:[1,2,1,""],request_devices:[1,2,1,""],sync_device_status:[1,2,1,""]},"alab_management.device_view.device_view.DevicesLock":{devices:[1,2,1,""],release:[1,2,1,""]},"alab_management.executor":{Executor:[0,1,1,""],ParameterError:[0,5,1,""]},"alab_management.executor.Executor":{run:[0,2,1,""],submit_task:[0,2,1,""]},"alab_management.experiment_manager":{ExperimentManager:[0,1,1,""]},"alab_management.experiment_manager.ExperimentManager":{handle_pending_experiments:[0,2,1,""],mark_completed_experiments:[0,2,1,""],run:[0,2,1,""]},"alab_management.experiment_view":{experiment:[2,0,0,"-"],experiment_view:[2,0,0,"-"]},"alab_management.experiment_view.experiment":{InputExperiment:[2,1,1,""]},"alab_management.experiment_view.experiment.InputExperiment":{name:[2,4,1,""],samples:[2,4,1,""],tasks:[2,4,1,""]},"alab_management.experiment_view.experiment_view":{ExperimentStatus:[2,1,1,""],ExperimentView:[2,1,1,""]},"alab_management.experiment_view.experiment_view.ExperimentStatus":{COMPLETED:[2,4,1,""],PENDING:[2,4,1,""],RUNNING:[2,4,1,""]},"alab_management.experiment_view.experiment_view.ExperimentView":{create_experiment:[2,2,1,""],get_experiment:[2,2,1,""],get_experiments_with_status:[2,2,1,""],update_experiment_status:[2,2,1,""],update_sample_task_id:[2,2,1,""]},"alab_management.lab_manager":{LabManager:[0,1,1,""],ResourcesRequest:[0,1,1,""]},"alab_management.lab_manager.LabManager":{get_sample:[0,2,1,""],move_sample:[0,2,1,""],request_resources:[0,2,1,""]},"alab_management.lab_manager.ResourcesRequest":{preprocess:[0,2,1,""]},"alab_management.logger":{DBLogger:[0,1,1,""],LoggingLevel:[0,1,1,""],LoggingType:[0,1,1,""]},"alab_management.logger.DBLogger":{filter_log:[0,2,1,""],log:[0,2,1,""],log_amount:[0,2,1,""],log_characterization_result:[0,2,1,""],log_device_signal:[0,2,1,""],system_log:[0,2,1,""]},"alab_management.logger.LoggingLevel":{CRITICAL:[0,4,1,""],DEBUG:[0,4,1,""],ERROR:[0,4,1,""],FATAL:[0,4,1,""],INFO:[0,4,1,""],WARN:[0,4,1,""],WARNING:[0,4,1,""]},"alab_management.logger.LoggingType":{CHARACTERIZATION_RESULT:[0,4,1,""],DEVICE_SIGNAL:[0,4,1,""],OTHER:[0,4,1,""],SAMPLE_AMOUNT:[0,4,1,""],SYSTEM_LOG:[0,4,1,""]},"alab_management.sample_view":{sample:[3,0,0,"-"],sample_view:[3,0,0,"-"]},"alab_management.sample_view.sample":{Sample:[3,1,1,""],SamplePosition:[3,1,1,""]},"alab_management.sample_view.sample.Sample":{name:[3,4,1,""],position:[3,4,1,""],task_id:[3,4,1,""]},"alab_management.sample_view.sample.SamplePosition":{SEPARATOR:[3,4,1,""],description:[3,4,1,""],name:[3,4,1,""],number:[3,4,1,""]},"alab_management.sample_view.sample_view":{SamplePositionRequest:[3,1,1,""],SamplePositionStatus:[3,1,1,""],SamplePositionsLock:[3,1,1,""],SampleView:[3,1,1,""]},"alab_management.sample_view.sample_view.SamplePositionRequest":{check_number:[3,2,1,""],from_py_type:[3,2,1,""],from_str:[3,2,1,""],number:[3,4,1,""],prefix:[3,4,1,""]},"alab_management.sample_view.sample_view.SamplePositionStatus":{EMPTY:[3,4,1,""],LOCKED:[3,4,1,""],OCCUPIED:[3,4,1,""]},"alab_management.sample_view.sample_view.SamplePositionsLock":{release:[3,2,1,""],sample_positions:[3,2,1,""]},"alab_management.sample_view.sample_view.SampleView":{add_sample_positions_to_db:[3,2,1,""],clean_up_sample_position_collection:[3,2,1,""],create_sample:[3,2,1,""],get_available_sample_position:[3,2,1,""],get_sample:[3,2,1,""],get_sample_position:[3,2,1,""],get_sample_position_status:[3,2,1,""],is_unoccupied_position:[3,2,1,""],lock_sample_position:[3,2,1,""],move_sample:[3,2,1,""],release_sample_position:[3,2,1,""],request_sample_positions:[3,2,1,""],update_sample_task_id:[3,2,1,""]},"alab_management.task_view":{task:[4,0,0,"-"],task_view:[4,0,0,"-"]},"alab_management.task_view.task":{BaseTask:[10,1,1,""],add_task:[4,3,1,""],get_all_tasks:[4,3,1,""]},"alab_management.task_view.task.BaseTask":{__init__:[10,2,1,""],required_resources:[4,2,1,""],run:[10,2,1,""]},"alab_management.task_view.task_view":{TaskStatus:[4,1,1,""],TaskView:[4,1,1,""]},"alab_management.task_view.task_view.TaskStatus":{COMPLETED:[4,4,1,""],ERROR:[4,4,1,""],PAUSED:[4,4,1,""],READY:[4,4,1,""],REQUESTING_RESOURCE:[4,4,1,""],RUNNING:[4,4,1,""],STOPPED:[4,4,1,""],WAITING:[4,4,1,""]},"alab_management.task_view.task_view.TaskView":{create_task:[4,2,1,""],get_ready_tasks:[4,2,1,""],get_status:[4,2,1,""],get_task:[4,2,1,""],try_to_mark_task_ready:[4,2,1,""],update_status:[4,2,1,""],update_task_dependency:[4,2,1,""]},alab_management:{config:[0,0,0,"-"],db:[0,0,0,"-"],device_view:[1,0,0,"-"],executor:[0,0,0,"-"],experiment_manager:[0,0,0,"-"],experiment_view:[2,0,0,"-"],lab_manager:[0,0,0,"-"],logger:[0,0,0,"-"],sample_view:[3,0,0,"-"],task_view:[4,0,0,"-"]}},objnames:{"0":["py","module","Python module"],"1":["py","class","Python class"],"2":["py","method","Python method"],"3":["py","function","Python function"],"4":["py","attribute","Python attribute"],"5":["py","exception","Python exception"]},objtypes:{"0":"py:module","1":"py:class","2":"py:method","3":"py:function","4":"py:attribute","5":"py:exception"},terms:{"127":5,"27017":9,"502":5,"abstract":[1,4,5,6,10],"case":0,"class":[0,1,2,3,4,5,6,10],"default":[3,9],"enum":[0,1,2,3,4],"float":10,"function":[0,1,3,4,5,10],"import":[5,6,10],"int":[0,1,3,5],"long":[5,10],"new":[0,3,4],"return":[0,1,2,3,4,5,10],"super":[5,10],"true":1,"try":[0,3,4,10],"while":[4,10],And:0,But:[5,10],For:[5,9],ROS:6,The:[0,1,2,3,4,5,6,9,10],There:1,With:6,__exit__:[1,3],__init__:[5,9,10],_devicetyp:1,_id:3,_resource_lock:0,_sampl:2,_task:2,abc:[1,4],about:[1,4,5,10],absolut:0,access:[0,7],accord:9,acquir:0,actual:[0,3],acycl:6,add:[0,2,4],add_devic:[1,5],add_devices_to_db:1,add_sample_positions_to_db:3,add_task:[4,10],address:5,after:3,aim:6,alab:[6,9],alab_manag:[5,10],alabconfig:0,all:[0,1,3,4,5,6,10],alloc:[4,10],allow:[0,6],alreadi:[1,3],also:[0,1,2,4,6,9,10],alwai:[5,10],amount:0,ani:[0,1,2,3,4,5,10],api:1,appear:[1,3],architectur:6,arg:[5,10],assign:[0,2,4,6,9,10],attribut:[1,5],authent:[0,9],automat:[1,4,9,10],autonom:6,avail:[0,1,3,4,10],base:[0,1,2,3,4],basedevic:[1,4,5,6],basemodel:[0,2,3],basetask:[4,6,10],basic:[0,3,6],batch:6,batteri:0,been:[2,3],befor:[4,9],belong:0,besid:9,between:6,block:1,bool:[1,3],briefli:3,bson:3,call:[1,3,4,10],can:[0,1,3,4,5,6,9,10],cannot:[3,4,10],certain:[0,6],character:0,characterization_result:0,charg:0,check:[1,3,4],check_numb:3,chemic:[0,6],classmethod:[0,3],classvar:[1,3],clean:1,clean_up_device_collect:1,clean_up_sample_position_collect:3,code:[5,6,10],collect:[0,1,2,3,4,6],come:0,command:[4,10],commun:6,complet:[0,2,4,6,10],conduct:6,config:[8,9],config_:0,configur:6,conflict:[4,10],connect:[5,9],construct:6,contain:6,content:8,context:[1,3,4,10],conveni:0,convert:0,coordin:[1,3,5],core:0,creat:[2,3,6],create_experi:2,create_sampl:3,create_task:4,creation:2,critic:0,current:[3,4,6,10],custom:[0,5,7,9,10],cycl:6,dag:6,dashboard:1,data:[0,2,3,4,10],databas:[0,1,2,3,4,6,7,9,10],dblogger:[0,10],debug:0,def:[1,5,10],defin:[1,3,4,6,9],definit:[1,6,7],depend:6,describ:[1,3,5,6],descript:[1,3,5],dest:[4,10],devic:[0,4,6,7,8,9,10],device_1:9,device_2:9,device_3:9,device_nam:1,device_name_1:1,device_sign:0,device_typ:1,device_view:[0,8],devicelock:1,devices_and_posit:[4,10],devices_and_sample_posit:0,deviceslock:1,devicestatu:1,devicetyp:0,deviceview:[1,6],dict:[0,1,2,3,4],differ:0,dir:[5,9,10],direct:6,directli:3,directori:9,discuss:7,doe:[1,5],doesn:[1,5,10],done:[2,6],driver:[5,6],drop:3,duplic:1,dure:[0,4],each:[0,6],easili:6,els:[0,3],emerg:[1,5],emergent_stop:[1,5],empti:[3,6],encount:4,entri:[1,3,4],error:[0,1,4],event:0,exampl:[1,4,5,9,10],except:0,execut:[0,4,5,10],executor:8,exist:3,exit:3,exp_id:2,experi:[0,8],experiment_manag:8,experiment_view:[0,8],experimentmanag:0,experimentstatu:2,experimentview:2,extens:6,fatal:0,file:0,filter:2,filter_log:0,find:0,finish:4,flag:0,flexibl:6,folder:7,follow:2,format:[0,1,2,3,6],found:1,from:[0,1,4,5,6,10],from_py_typ:3,from_str:3,froze_config:0,frozen:0,frozen_config:0,furnac:[0,1,4,5,10],furnace_1:[0,5],furnace_t:[1,5],furnacecontrol:5,gener:9,geograph:3,get:[0,1,2,3,4,10],get_al:1,get_all_devic:1,get_all_task:4,get_available_devic:1,get_available_sample_posit:3,get_collect:0,get_devic:1,get_experi:2,get_experiments_with_statu:2,get_ready_task:4,get_sampl:[0,3],get_sample_posit:3,get_sample_position_statu:3,get_statu:[1,4],get_task:4,get_temperatur:[4,10],git:6,github:6,given:1,going:1,graph:6,great:6,handl:[4,9],handle_pending_experi:0,has:[0,1,2,3,4,6,9,10],have:[0,1,3,6,7],heat:[1,5,6,10],here:[1,4,5,10],higher:0,hold:[1,3,4,5,6],host:[6,9],how:[1,4,5,7,9,10],identifi:[1,3,5,10],idl:[1,6],ids:[4,6],implement:6,includ:[1,3,5],independ:0,index:6,indic:[1,3],info:[0,3,4],inform:[0,1,5,6,10],inherit:[1,4,5,6,10],initi:[3,5],input:3,inputexperi:2,insert:[1,2,3,4],insid:[0,1,4,5,10],inside_furnac:[4,10],instanc:[1,3,6],instead:0,intend:2,introduc:9,is_run:[1,4,10],is_unoccupied_posit:3,iter:0,its:[2,3,4,6],itself:9,just:[3,6,9],kind:5,know:0,kwarg:[5,10],lab:[1,2,3,4,5,9,10],lab_manag:[4,8,10],labmanag:[0,2,6,10],later:2,least:7,level:0,life:6,like:[6,9],list:[0,1,2,3,4,5,6,10],load:[5,9,10],local:7,localhost:9,lock:[3,6],lock_sample_posit:3,log:[0,4,10],log_amount:0,log_characterization_result:0,log_data:0,log_device_sign:[0,4,10],logger:[4,8,10],logging_typ:0,logginglevel:0,loggingtyp:0,longer:1,look:9,loop:0,mai:[1,6,9],main:[0,2,3],make:[5,10],manag:[0,1,2,3,4,9,10],manual:[1,5],map:[1,5],mappingproxi:0,mark:[0,4],mark_completed_experi:0,match:3,matter:[1,5,10],maximum:1,mean:3,method:[0,1,2,3,5],modifi:0,modul:[8,9],mongocli:0,mongodb:[6,7],more:[1,5,9,10],move:[0,4,10],move_sampl:[0,3],moving_task:[4,10],multipl:[0,6],must:[4,6,7],name:[0,1,2,3,4,5,9,10],nameerror:1,need:[0,1,3,5,6,9,10],need_releas:[1,3],neither:3,next:4,next_task:4,none:[0,1,3,4],nor:3,note:0,now:[1,4],number:[0,3,4,10],object:[0,1,2,3,4,5],objectid:[0,1,2,3,4,10],occupi:[1,3,6],occupy_devic:1,okai:9,old:4,onc:5,one:[0,1,3,4,7],ones:1,onli:[0,1,5],only_idl:1,oper:6,option:[1,2,3,4,10],other:[0,4,10],our:6,out:0,outsid:1,over:[0,4,6,10],overwrit:4,ownership:[1,4,10],packag:[6,8,9],page:6,param:0,paramet:[0,1,2,3,4,5,6,10],parametererror:0,parent:4,pars:0,pass:4,password:9,path:0,pattern:0,paus:4,pend:[0,2,4,6,10],place:6,platform:6,pleas:[5,9],port:[5,9],posit:[0,1,3,4,5,6,10],position_prefix:3,pre_task:4,predefin:[0,6],prefix:[0,3],preprocess:0,prev:4,prev_task:4,prevent:[4,10],previou:[4,6],princip:0,procedur:0,process:[0,2],project:6,project_root:9,properli:[5,10],properti:[0,1,3,5],provid:[1,5,6,9,10],put:[0,2,6],pydant:[0,2,3],pymongo:6,python:[6,7,9],queri:0,queue:2,rack:6,rais:[0,1],rang:0,raw:2,reach:[5,10],read:[0,6],readi:[0,1,4,6],real:[1,5,6],recommend:[5,10],record:[0,6,10],refer:[4,5,6,7,9,10],regist:[1,4,9],registri:[1,4],releas:[1,3,4,10],release_devic:1,release_sample_posit:3,remot:7,renew:5,replac:0,repo:[5,9],repositori:6,repres:[0,4,6,10],represent:6,request:[0,1,3,4,6,10],request_devic:1,request_resourc:[0,4,10],request_sample_posit:3,requesting_resourc:4,requir:[2,4,6],required_resourc:4,reserv:3,resourc:[0,3,4,6,9,10],resource_request:0,resourcesrequest:0,result:0,robot:6,robot_arm:1,robotarm:1,root:[5,10],run:[0,1,2,4,6,9,10],run_program:[4,10],same:[0,1,3,4,10],sampl:[0,1,2,4,5,6,8,10],sample_1:10,sample_2:10,sample_3:10,sample_4:10,sample_amount:0,sample_id:[0,2,3],sample_posit:[1,3,4,5,10],sample_position_1:0,sample_position_prefix:3,sample_position_prefix_1:3,sample_view:[0,8],sampleposit:[1,3,5],samplepositionrequest:[0,3],samplepositionslock:3,samplepositionstatu:3,sampleview:[3,6],scan:0,search:6,second:[1,3],section:9,see:[0,1,2],self:[1,4,5,10],send:[4,10],sensor:0,separ:3,serv:9,set:[1,3,5,7],setpoint:[4,10],setup:7,shall:1,sharabl:6,share:[4,6,10],should:[0,1,2,3,4,5,6,9,10],signal:0,similar:10,sinc:[0,6],skip:3,snippet:6,some:[0,1,3,4,5,6,9],someth:[1,6],sometim:0,sourc:[0,1,2,3,4,5,10],specifi:[0,1,3,5,6,9],start:[0,4],startwith:3,statu:[1,2,3,4],still:[1,6],stop:[1,4,5,6],store:[0,1,4,5,9],str:[0,1,2,3,4,5],string:[0,3],structur:[3,9],submit:[0,2,4,6],submit_task:0,submodul:8,subpackag:8,sure:[5,10],sync:1,sync_device_statu:1,synthesi:6,system:[0,1,5,6,9,10],system_log:0,take:[0,4,10],task:[0,1,2,3,6,7,8,9],task_1:9,task_2:9,task_3:9,task_entri:0,task_id:[0,1,2,3,4,10],task_typ:4,task_view:[0,8],taskstatu:4,taskview:4,tell:3,temperatur:[0,4,6,10],temporari:[1,5],than:[0,1],them:[0,1,5,6,9],thi:[0,1,2,3,4,5,6,7,9,10],thread:0,three:6,throughout:6,time:[0,5],timeout:[1,3],toml:9,track:6,transfer:[1,5],try_to_mark_task_readi:4,tupl:[3,10],two:6,type:[0,1,2,3,4,5],uid:3,under:[0,6],union:[0,3,4],uniqu:[1,3,5],unknown:1,unlock:3,unoccupi:3,until:[0,1,3,4,10],updat:[0,2,3,4,6,10],update_experiment_statu:2,update_sample_task_id:[2,3],update_statu:4,update_task_depend:4,usabl:1,use:[0,1,2,4,5,6,9,10],used:[0,1,3,6],user:[1,2,5,6],usernam:9,usual:[0,1,9],valid:[0,3],valu:[0,1,2,3,4,6],valueerror:1,vertex:6,via:6,view:[0,1,2,3,4,6,10],voltag:0,wait:[1,4,6],want:[0,10],warn:0,websit:6,weight:0,well:[1,6],what:6,when:[0,1,3,4,5,6,10],where:[0,1,5,9,10],whether:[1,3],which:[0,1,2,3,4,5,6,9,10],within:0,work:[6,9],workflow:[0,6],working_dir:9,wrapper:[0,6],write:[2,5],wrong:0,wrote:0,xrd:0,you:[0,1,3,4,5,6,7,9,10],your:[5,9]},titles:["alab_management package","alab_management.device_view package","alab_management.experiment_view package","alab_management.sample_view package","alab_management.task_view package","Defining a new device","Overview","Installation","alab_management","Set up definition folder","Defining a new task"],titleterms:{"new":[5,10],For:7,alab_manag:[0,1,2,3,4,8],config:0,configur:9,content:[0,1,2,3,4],data:6,defin:[5,10],definit:9,develop:7,devic:[1,5],device_view:1,executor:[0,6],experi:[2,6],experiment_manag:0,experiment_view:2,file:9,folder:9,indic:6,instal:7,lab:6,lab_manag:0,logger:0,manag:6,modul:[0,1,2,3,4,6],next:[7,9],overview:6,packag:[0,1,2,3,4],prerequisit:7,purpos:7,regist:[5,10],sampl:3,sample_view:3,set:9,statu:6,storag:6,submodul:[0,1,2,3,4],subpackag:0,tabl:6,task:[4,10],task_view:4,terminolog:6,what:[7,9]}})