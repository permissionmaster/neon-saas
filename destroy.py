import boto3, json, time
ec2=boto3.client("ec2"); elb=boto3.client("elbv2"); s3=boto3.client("s3")

def delete_json():
    with open("infra.json") as f:
        i=json.load(f)
    # GWLB
    try:
        lbs=elb.describe_load_balancers(LoadBalancerArns=[i["gwlb"]])
        for lb in lbs["LoadBalancers"]:
            elb.delete_load_balancer(LoadBalancerArn=lb["LoadBalancerArn"])
            print("⏳ waiting lb delete..."); time.sleep(30)
    except: pass
    # VPC
    for vpc in [i["room_vpc"], i["internal_vpc"]]:
        if not vpc: continue
        # subnets
        subs=[s["SubnetId"] for s in ec2.describe_subnets(Filters=[{"Name":"vpc-id","Values":[vpc]}])["Subnets"]]
        for sn in subs: ec2.delete_subnet(SubnetId=sn)
        # nat/igw
        igws=[g["InternetGatewayId"] for g in ec2.describe_internet_gateways(
            Filters=[{"Name":"attachment.vpc-id","Values":[vpc]}])["InternetGateways"]]
        for g in igws:
            ec2.detach_internet_gateway(InternetGatewayId=g, VpcId=vpc)
            ec2.delete_internet_gateway(InternetGatewayId=g)
        # vpc
        ec2.delete_vpc(VpcId=vpc)
    # bucket
    bk=i["log_bucket"]
    objs=s3.list_objects_v2(Bucket=bk).get("Contents",[])
    if objs:
        s3.delete_objects(Bucket=bk, Delete={"Objects":[{"Key":o["Key"]} for o in objs]})
    s3.delete_bucket(Bucket=bk)
    print("🗑️  All gone")

if __name__=="__main__":
    delete_json()
