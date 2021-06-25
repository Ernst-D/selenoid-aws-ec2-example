from nested_lookup import nested_lookup
import boto3
import requests
import sys
import xml.etree.ElementTree as gfg  

asg = boto3.client('autoscaling')
ec2 = boto3.client('ec2')
asg_group_names=['selenoid_linux','selenoid_windows']

#some helper functions
def flatten_list(_2d_list):
    flat_list = []
    for element in _2d_list:
        if type(element) is list:
            for item in element:
                flat_list.append(item)
        else:
            flat_list.append(element)
    return flat_list
def flat_map(_2d_list):
    return [item for subl in _2d_list for item in subl]
def getList(dict): 
    return dict.values()

#get all instances from autoscale group
response_asg_instances = asg.describe_auto_scaling_groups(
    AutoScalingGroupNames = [asg_group_names[0]] 
)
asg_instances = nested_lookup(
    key = "Instances",
    document = response_asg_instances,
    wild = True
)

#get all Healthy and InService instances from group and put them to separate list
sor_arr = [];
for instance in flatten_list(asg_instances[0]):
    if instance["HealthStatus"].upper() == "HEALTHY" and instance["LifecycleState"] == "InService":
        result = nested_lookup(
            key = "InstanceId",
            document = instance
            )
        sor_arr.append(result)

#get all ec2 instances based on InstancesIds we have in asg 
response_ec2 = ec2.describe_instances(
    InstanceIds=flat_map(sor_arr),
)
#retrieve information we need for quota xml
ec2_ipadresses = nested_lookup(
    key= "PublicIp",
    document = response_ec2,
)
ec2_regions = nested_lookup(
    key= "AvailabilityZone",
    document = response_ec2,
)


ipAdresses = list(set(ec2_ipadresses))
#one selenoid per instance - same port
selenoid_port = "4444"
regions = list(set(ec2_regions))

#check whether selenoids are working. If not - script execution will be finished
try:
    r = requests.get(f'http://{ipAdresses[0]}:{selenoid_port}/status')
    browsers = r.json()["browsers"]
    print(browsers)
except:
    print("no connection")
    sys.exit(1)

#retrieve browser versions. We have same config (browsers.json) for every selenoid 
browserVersions = [];
for version in getList(browsers):
    browserVersions.append(flatten_list(list(version.keys())))


browserItems = browsers.items();

#generating the quota xml
#browser => version => region => host
root = gfg.Element("qa:browsers")
root.set("xmlns:qa","urn:config.gridrouter.qatools.ru")
for browserItem in browsers.items():
    print(type(browserItem))
    browser = gfg.Element("browser") 
    browser.set("name",browserItem[0])
    browser.tail = "\n\t"
    root.append(browser)
    for v in browserItem[1]:
        print("v in browserItem",v)
        version = gfg.SubElement(browser,"version")
        version.set("number",v)
        version.tail = "\n\t"
        for r in regions:
            print(r)
            region = gfg.SubElement(version,"region")
            region.set("name",r)
            region.tail = "\n\t"
            for ip in ipAdresses:
                print(ip)
                host= gfg.SubElement(region,"host")
                host.set("name",ip)
                host.set("port",selenoid_port)
                host.set("count","1")
                host.tail = "\n\t"
                 
tree = gfg.ElementTree(root) 


#point quota xml to the directory which balancer requires   
# with open ("/etc/grid-router/quota/linux.xml", "wb") as files : 
#     tree.write(files) 

#linux.xml - example of output. It's a bit hard to prettify xml, generated with ElementTree 
with open ("linux.xml", "wb") as files : 
    tree.write(files) 



