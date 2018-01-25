from troposphere import Template, cloudformation, route53, Output, Export, Sub, Parameter, Ref, GetAtt, Join
from uuid import uuid4

t = Template()


def update_dummy_wch(template):
    template.add_resource(cloudformation.WaitConditionHandle(
        str(uuid4()).replace("-", "")
    ))


update_dummy_wch(t)

print(t.to_json())
