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
    Description="Parameter from config.json init file.",
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
