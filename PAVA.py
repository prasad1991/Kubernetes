#!/usr/bin/python
# vim: set fileencoding=<encoding name> :
import os,sys 
import time
import random
import json
import os
import re
import sys
import kubernetes.client
from pint        import UnitRegistry
from collections import defaultdict
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
import time
import requests

config.load_kube_config()
c1=client.Configuration()
c1.verify_ssl=False

scheduler_name="PAVA"
##################### Core api of Kubernetes  from which we are gathering data in YAML ###############################################
v1=client.CoreV1Api()
ret = v1.list_pod_for_all_namespaces(watch=False)
group_priority =[]
dict_obj1=[]
group_pod={}
group_name=[]
#######################################  available PODs from core api server  of Kubernetes for scheduling  ######################

print ("\n \n \n \n Running pod on current kubernetes cluster \n \n \n \n  ")
for j in ret.items:
    print(" %s\t%s\t%s\t%s\t%s\t%s" % (j.status.pod_ip, j.metadata.namespace, j.metadata.name,j.spec.priority,j.spec.scheduler_name,j.status.phase))


################################## priority aware algorithm works ####################################


print("\n \n \n \n scheduling pod details are as below \n \n  ")

for i in ret.items:
    Scheduling_priority =[]
    if i.spec.scheduler_name=='PAVA':
        print("%s\t%s\t%s\t%s\t%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name,i.spec.priority,i.spec.scheduler_name,i.status.phase,i.spec.priority_class_name))  
        group_priority.append(i.spec.priority) 
        group_name.append(i.metadata.name)
        group_pod=dict(zip(group_name,group_priority))
        Sorted_poddict=sorted(group_pod.items(),key=lambda kv:(kv[1],kv[0]),reverse=True)

print ("\n \n  pods details captured in dictionary  before  sorting  %s \n \n " %group_pod)
   

########################### Scheduled POD with highest priority first#########################################################

        
print("sorted PODs namespaces and priority value %s"%sorted(group_pod.items(),key=lambda kv:(kv[1],kv[0]),reverse=True))



########################## Selecting best slave nodes  for deployment on the basis of CPU,Memory and Network  ################################
__all__ = ["compute_allocated_resources"]

def compute_allocated_resources():
    ureg = UnitRegistry()
    ureg.load_definitions('kubernetes_units.txt')

    Q_   = ureg.Quantity
    data = {}

    # doing this computation within a k8s cluster
 #   config.load_incluster_config()
    config.load_kube_config()
    core_v1 =client.CoreV1Api()

    for node in core_v1.list_node().items:
        stats          = {}
        node_name      = node.metadata.name
        allocatable    = node.status.allocatable
        print allocatable 
        max_pods       = int(int(allocatable["pods"]) * 1.5)
        field_selector = ("status.phase!=Succeeded,status.phase!=Failed," +
                          "spec.nodeName=" + node_name)

        stats["cpu_alloc"] = Q_(allocatable["cpu"])
        print stats["cpu_alloc"]
        stats["mem_alloc"] = Q_(allocatable["memory"])

        pods = core_v1.list_pod_for_all_namespaces(limit=max_pods,
                                                   field_selector=field_selector).items

        # compute the allocated resources
        cpureqs,cpulmts,memreqs,memlmts = [], [], [], []
        for pod in pods:
            for container in pod.spec.containers:
                res  = container.resources
                reqs = defaultdict(lambda: 0, res.requests or {})
                lmts = defaultdict(lambda: 0, res.limits or {})
                cpureqs.append(Q_(reqs["cpu"]))
                memreqs.append(Q_(reqs["memory"]))
                cpulmts.append(Q_(lmts["cpu"]))
                memlmts.append(Q_(lmts["memory"]))

        stats["cpu_req"]     = sum(cpureqs)
        print stats["cpu_req"]
        stats["cpu_lmt"]     = sum(cpulmts)
        print stats["cpu_lmt"]
        stats["cpu_req_per"] = (stats["cpu_req"] / stats["cpu_alloc"] * 100)
        print stats["cpu_alloc"]
        print stats["cpu_req_per"]
        stats["cpu_lmt_per"] = (stats["cpu_lmt"] / stats["cpu_alloc"] * 100)
        stats["mem_req"]     = sum(memreqs)
        stats["mem_lmt"]     = sum(memlmts)
        stats["mem_req_per"] = (stats["mem_req"] / stats["mem_alloc"] * 100)
        stats["mem_lmt_per"] = (stats["mem_lmt"] / stats["mem_alloc"] * 100)

        data[node_name] = stats

    return data

data1= compute_allocated_resources()
print (data1)


################################################Watch function to check POD and append value ############################################
w = watch.Watch()
for event in w.stream(v1.list_namespaced_pod,"default"):
    if event['object'].status.phase == "Pending"  and event['object'].status.conditions == None and
    event['object'].spec.scheduler_name == scheduler_name:
       # print event['object']
        r1 = event['object'].metadata.name
        #print event['object'].namespace
        print r1
        ready_nodes=[]
        for n in v1.list_node().items:
            for status in n.status.conditions:
                if status.status == "True" and status.type == "Ready":
                    ready_nodes.append(n.metadata.name)
        node="slave-1"
        print group_pod
        group_name=list(group_pod.keys())
        for item in group_name:  
            name=item
            print name
            namespace="default" 
            target=client.V1ObjectReference(kind='Node',api_version = 'v1', name = node,namespace="default")
            meta=client.V1ObjectMeta(name=name)
            body= kubernetes.client.V1Binding(target=target,metadata=meta)
            print body
            try:
                res = v1.create_namespaced_binding(namespace=namespace,body=body,_preload_content=False)
                print res 
            except Exception as a:
                print ("Exception when calling CoreV1Api->create_namespaced_binding: %s\n" % a)
