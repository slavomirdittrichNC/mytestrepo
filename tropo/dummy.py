from troposphere import Template, cloudformation, route53, Output, Export, Sub, Parameter, Ref, GetAtt, Join
from uuid import uuid4

t = Template()

# def update_dummy_wch(template):
#     template.add_resource(cloudformation.WaitConditionHandle(
#         str(uuid4()).replace("-", "")
#     ))
#
#
# update_dummy_wch(t)


dummy_type_parameter = t.add_parameter(Parameter(
    "DummyTypeParameter",
    Type="String",
    Description="Type of dummy stack [UAT, PROD] from config-uat.json and config-prod.json files.",
    Default=""
))

dummy_resource = t.add_resource(cloudformation.WaitConditionHandle(
    str(uuid4()).replace("-", "")
))

t.add_output(Output(
    "DummyResourceOutput",
    Description="Dummy resource name",
    Value=Ref(dummy_resource),
))

print(t.to_json())
