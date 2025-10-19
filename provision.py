import boto3, json, uuid, time
from datetime import datetime

region = boto3.session.Session().region_name or "us-east-1"
ec2 = boto3.client("ec2", region_name=region)
elb = boto3.client("elbv2", region_name=region)
s3  = boto3.client("s3", region_name=region)
logs= boto3.client("logs", region_name=region)

TAG = {"Project":"neon", "Customer":"auto"}

def tag(_type):
    return [{"Key":k,"Value":v} for k,v in {**TAG,**{"Type":_type}}.items()]

def create_vpc_pair():
    # 1) 방 VPC
    room = ec2.create_vpc(CidrBlock="10.1.0.0/16")
    rvpc = room["Vpc"]["VpcId"];  ec2.create_tags(Resources=[rvpc], Tags=tag("room"))
    # 2) 내부 VPC
    intl = ec2.create_vpc(CidrBlock="10.2.0.0/16")
    ivpc = intl["Vpc"]["VpcId"];  ec2.create_tags(Resources=[ivpc], Tags=tag("internal"))
    return rvpc, ivpc

def create_room_subnets(vpc_id):
    azs = [az["ZoneName"] for az in ec2.describe_availability_zones()["AvailabilityZones"]][:2]
    subs=[]; rt_id=None
    for i,az in enumerate(azs):
        sn=ec2.create_subnet(VpcId=vpc_id, CidrBlock=f"10.1.{i}.0/24", AvailabilityZone=az)
        subs.append(sn["Subnet"]["SubnetId"])
    ec2.create_tags(Resources=subs, Tags=tag("room-sub"))
    # IGW
    igw=ec2.create_internet_gateway(); igw_id=igw["InternetGateway"]["InternetGatewayId"]
    ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
    # route
    rt_id=ec2.describe_route_tables(Filters=[{"Name":"vpc-id","Values":[vpc_id]}])["RouteTables"][0]["RouteTableId"]
    ec2.create_route(RouteTableId=rt_id, DestinationCidrBlock="0.0.0.0/0", GatewayId=igw_id)
    return subs, igw_id

def create_internal_subnets(vpc_id):
    azs = [az["ZoneName"] for az in ec2.describe_availability_zones()["AvailabilityZones"]][:2]
    nat_subs=[]; priv_subs=[]
    for i,az in enumerate(azs):
        nat=ec2.create_subnet(VpcId=vpc_id, CidrBlock=f"10.2.{i}.0/24", AvailabilityZone=az)
        priv=ec2.create_subnet(VpcId=vpc_id, CidrBlock=f"10.2.{i+10}.0/24", AvailabilityZone=az)
        nat_subs.append(nat["Subnet"]["SubnetId"]); priv_subs.append(priv["Subnet"]["SubnetId"])
    ec2.create_tags(Resources=nat_subs, Tags=tag("nat-sub"))
    ec2.create_tags(Resources=priv_subs, Tags=tag("priv-sub"))
    # NAT
    eip=ec2.allocate_address(Domain="vpc")
    nat_gw=ec2.create_nat_gateway(SubnetId=nat_subs[0], AllocationId=eip["AllocationId"])
    # private RT
    rt_id=ec2.describe_route_tables(Filters=[{"Name":"vpc-id","Values":[vpc_id]}])["RouteTables"][0]["RouteTableId"]
    ec2.create_route(RouteTableId=rt_id, DestinationCidrBlock="0.0.0.0/0", NatGatewayId=nat_gw["NatGateway"]["NatGatewayId"])
    return priv_subs

def create_gwlb(subnets):
    vpc_id = ec2.describe_subnets(SubnetIds=[subnets[0]])["Subnets"][0]["VpcId"]
    tg=elb.create_target_group(Name=f"neon-tg-{uuid.uuid4().hex[:8]}", Protocol="GENEVE", Port=6081, VpcId=vpc_id)
    lb=elb.create_load_balancer(Name=f"neon-gwlb-{uuid.uuid4().hex[:8]}", Subnets=subnets, Type="gateway")
    elb.create_listener(LoadBalancerArn=lb["LoadBalancers"][0]["LoadBalancerArn"],
                        Protocol="GENEVE", Port=6081,
                        DefaultActions=[{"Type":"forward","TargetGroupArn":tg["TargetGroups"][0]["TargetGroupArn"]}])
    return lb["LoadBalancers"][0]["LoadBalancerArn"]

def create_log_bucket():
    bucket=f"neon-logs-{uuid.uuid4().hex[:8]}-{region}"
    s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint":region})
    return bucket

def create_log_group():
    lg=f"/neon/{uuid.uuid4().hex[:8]}"
    logs.create_log_group(logGroupName=lg)
    return lg

def run():
    print("🔨 Creating isolated ROOM + INTERNAL ...")
    rvpc, ivpc = create_vpc_pair()
    rsubs, _   = create_room_subnets(rvpc)
    ipriv      = create_internal_subnets(ivpc)
    glb_arn    = create_gwlb(rsubs)
    bucket     = create_log_bucket()
    loggrp     = create_log_group()
    info={"room_vpc":rvpc,"internal_vpc":ivpc,"gwlb":glb_arn,"log_bucket":bucket,"log_group":loggrp}
    with open("infra.json","w") as f:
        json.dump(info, f)
    print("✅ infra.json saved")
    return info

if __name__=="__main__":
    run()
