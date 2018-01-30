from troposphere import GetAtt, Parameter, Ref, Join, Sub, Template, Output, Export
from troposphere import codebuild, codepipeline, iam, s3, sns
from awacs.aws import Policy, Allow, Statement, Principal, Action
import json


def main():
    # TODO:
    # - SNS topic is probably not complete
    # - BuildCopyCFNProject Encryption keys
    # - build_copy_cfn_project, validate_resource_project TimeoutInMinutes property
    # - Lambda function execute permissions
    # - Build role GetBucketTagging permissions. Only used in build-env step, may be obsolete in other scenarios
    # - Add customer name to CodeCommit repositories
    # - What to do with the password of the codecommit user?
    # - InputArtifact is not used in pipeline
    # - buildspec.env in project definition itself
    # - CodeCommitUser Permissions on troporepo and CFNvalidaterepo only!

    # INIT section

    template = Template()
    projectName = "dummy-mytestrepo"

    # PARAMETERS section

    github_oauth_token_parameter = template.add_parameter(Parameter(
        "GithubOauthToken",
        Type="String",
        Description="Github OAuthToken",
        NoEcho=True,
    ))

    github_owner_parameter = template.add_parameter(Parameter(
        "GithubOwner",
        Type="String",
        Description="Github owner",
        Default="cta-int",
    ))

    github_branch_parameter = template.add_parameter(Parameter(
        "GithubBranch",
        Type="String",
        Description="Github branch",
        Default="master",
    ))

    github_repository_parameter = template.add_parameter(Parameter(
        "GithubRepository",
        Type="String",
        Description="Github repository",
        Default="aws-bootstrap",
    ))

    # RESOURCES section

    approve_topic = template.add_resource(sns.Topic(
        "ApproveTopic",
        Subscription=[
            sns.Subscription(
                Endpoint="slavomir.dittrich@nordcloud.com",
                Protocol="email",
            )]
    ))

    artifact_store_s3_bucket = template.add_resource(s3.Bucket(
        "ArtifactStoreS3Bucket",
        AccessControl=s3.Private,
    ))

    # ROLES section

    cloud_formation_role = template.add_resource(iam.Role(
        "CloudFormationRole",
        AssumeRolePolicyDocument=Policy(
            Version="2012-10-17",
            Statement=[
                Statement(
                    Effect=Allow,
                    Principal=Principal("Service", "cloudformation.amazonaws.com"),
                    Action=[Action("sts", "AssumeRole")]
                )
            ]
        ),
        Path="/",
        Policies=[
            iam.Policy(
                PolicyName="CloudFormationNestedCFNAccessPolicy",
                PolicyDocument=Policy(
                    Version="2012-10-17",
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action("*")
                            ],
                            Resource=["*"]
                        )
                    ]
                )
            )
        ]
    ))

    code_build_role = template.add_resource(iam.Role(
        "CodeBuildRole",
        AssumeRolePolicyDocument=Policy(
            Version="2012-10-17",
            Statement=[
                Statement(
                    Effect=Allow,
                    Principal=Principal("Service", "codebuild.amazonaws.com"),
                    Action=[Action("sts", "AssumeRole")],
                )
            ]
        ),
        Path="/",
        Policies=[
            iam.Policy(
                PolicyName="CodeBuildAccessPolicy",
                PolicyDocument=Policy(
                    Version="2012-10-17",
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action("cloudformation", "Get*"),
                                Action("cloudformation", "Describe*"),
                                Action("cloudformation", "List*"),
                            ],
                            Resource=[
                                Sub("arn:aws:cloudformation:${AWS::Region}:${AWS::AccountId}:stack/${AWS::StackName}*"),
                            ]
                        ),
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action("ec2", "Describe*"),
                                Action("cloudformation", "ValidateTemplate"),
                                Action("elasticloadbalancing", "Describe*"),
                                Action("autoscaling", "Describe*"),
                                Action("iam", "Get*"),
                                Action("iam", "List*"),
                                Action("logs", "Describe*"),
                                Action("logs", "Get*"),
                                Action("tag", "Get*"),
                            ],
                            Resource=[
                                "*"
                            ]
                        ),
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action("logs", "CreateLogGroup"),
                                Action("logs", "CreateLogStream"),
                                Action("logs", "PutLogEvents"),
                            ],
                            Resource=[
                                Sub("arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/codebuild/*"),
                            ]
                        ),
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action("lambda", "ListFunctions"),
                                Action("lambda", "InvokeFunction"),
                            ],
                            Resource=[
                                "*",
                            ]
                        ),
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action("s3", "PutObject"),
                                Action("s3", "GetObject"),
                                Action("s3", "GetObjectVersion"),
                                Action("s3", "ListBucket"),
                            ],
                            Resource=[
                                Sub("arn:aws:s3:::codepipeline-${AWS::Region}-*"),
                                GetAtt(artifact_store_s3_bucket, "Arn"),
                                Join("", [GetAtt(artifact_store_s3_bucket, "Arn"), "/*"]),
                            ]
                        ),
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action("s3", "GetBucketTagging"),
                            ],
                            Resource=[
                                Sub("arn:aws:s3:::*"),
                            ]
                        )
                    ]
                )
            )
        ]
    ))

    code_pipeline_role = template.add_resource(iam.Role(
        "CodePipelineRole",
        AssumeRolePolicyDocument=Policy(
            Version="2012-10-17",
            Statement=[
                Statement(
                    Effect=Allow,
                    Principal=Principal("Service", "codepipeline.amazonaws.com"),
                    Action=[Action("sts", "AssumeRole")],
                )
            ]
        ),
        Path="/",
        Policies=[
            iam.Policy(
                PolicyName="CodePipelineAccessPolicy",
                PolicyDocument=Policy(
                    Version="2012-10-17",
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action("s3", "*")
                            ],
                            Resource=[
                                GetAtt(artifact_store_s3_bucket, "Arn"),
                                Join("", [GetAtt(artifact_store_s3_bucket, "Arn"), "/*"]),
                            ]
                        ),
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action("sns", "Publish"),
                            ],
                            Resource=[
                                Ref(approve_topic),
                            ]
                        ),
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action("codebuild", "StartBuild"),
                                Action("codebuild", "BatchGetBuilds"),
                            ],
                            Resource=[
                                Sub(
                                    "arn:aws:codebuild:${AWS::Region}:${AWS::AccountId}:project/" + projectName),
                            ]
                        ),
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action("lambda", "ListFunctions"),
                                Action("lambda", "InvokeFunction"),
                            ],
                            Resource=[
                                "*",
                            ]
                        ),
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action("iam", "PassRole"),
                            ],
                            Resource=[
                                GetAtt(cloud_formation_role, "Arn"),
                            ],
                        )
                    ]
                )
            )
        ]
    ))

    code_build_dummy = template.add_resource(codebuild.Project(
        "CodeBuildDummy",
        Source=codebuild.Source(
            Type="CODEPIPELINE"
        ),
        Artifacts=codebuild.Artifacts(
            Type="CODEPIPELINE"
        ),
        Description="Generate cloudformation templates",
        Environment=codebuild.Environment(
            ComputeType='BUILD_GENERAL1_SMALL',
            Image='aws/codebuild/python:3.3.6',
            Type='LINUX_CONTAINER',
        ),
        Name=projectName,
        ServiceRole=GetAtt(code_build_role, "Arn"),
    ))

    code_pipeline_dummy = template.add_resource(codepipeline.Pipeline(
        "CodePipelineDummy",
        Name="pipeline-" + projectName,
        RoleArn=GetAtt(code_pipeline_role, "Arn"),
        ArtifactStore=codepipeline.ArtifactStore(
            Type="S3",
            Location=Ref(artifact_store_s3_bucket),
        ),
        Stages=[
            codepipeline.Stages(
                Name="Source",
                Actions=[
                    codepipeline.Actions(
                        Name="Source",
                        ActionTypeId=codepipeline.ActionTypeID(
                            Category="Source",
                            Owner="ThirdParty",
                            Provider="GitHub",
                            Version="1",
                        ),
                        OutputArtifacts=[
                            codepipeline.OutputArtifacts(
                                Name="Source",
                            )
                        ],
                        Configuration={
                            "Branch": Ref(github_branch_parameter),
                            "Repo": Ref(github_repository_parameter),
                            "PollForSourceChanges": True,
                            "Owner": Ref(github_owner_parameter),
                            "OAuthToken": Ref(github_oauth_token_parameter),
                        },
                        RunOrder="1",
                    ),
                ]
            ),

            codepipeline.Stages(
                Name="Build",
                Actions=[
                    codepipeline.Actions(
                        Name="Build",
                        ActionTypeId=codepipeline.ActionTypeID(
                            Category="Build",
                            Owner="AWS",
                            Provider="CodeBuild",
                            Version="1",
                        ),
                        InputArtifacts=[
                            codepipeline.InputArtifacts(
                                Name="Source",
                            )
                        ],
                        OutputArtifacts=[
                            codepipeline.OutputArtifacts(
                                Name="Build",
                            )
                        ],
                        Configuration={
                            "ProjectName": Ref(code_build_dummy),
                        },
                        RunOrder="1",
                    ),
                ]
            ),

            codepipeline.Stages(
                Name="UAT",
                Actions=[
                    codepipeline.Actions(
                        Name="CreateUATStack",
                        InputArtifacts=[
                            codepipeline.InputArtifacts(
                                Name="Build",
                            )
                        ],
                        ActionTypeId=codepipeline.ActionTypeID(
                            Category="Invoke",
                            Owner="AWS",
                            Version="1",
                            Provider="Lambda",
                        ),
                        Configuration={
                            "FunctionName": "lambda-cfn-provider",
                            "UserParameters": Sub(json.dumps({
                                "ActionMode": "CREATE_UPDATE",
                                "ConfigPath": "Build::config.json",
                                "StackName": projectName + "-UAT",
                                "TemplatePath": "Build::dummy.json",
                            }))
                        },
                        OutputArtifacts=[
                            codepipeline.OutputArtifacts(
                                Name="CreateUATStack",
                            )
                        ],
                        RunOrder="1",
                    ),

                    codepipeline.Actions(
                        Name="CreatePRODChangeSet",
                        InputArtifacts=[
                            codepipeline.InputArtifacts(
                                Name="Build",
                            )
                        ],
                        ActionTypeId=codepipeline.ActionTypeID(
                            Category="Invoke",
                            Owner="AWS",
                            Version="1",
                            Provider="Lambda",
                        ),
                        Configuration={
                            "FunctionName": "lambda-cfn-provider",
                            "UserParameters": Sub(json.dumps({
                                "ActionMode": "CHANGE_SET_REPLACE",
                                "ChangeSetName": projectName + "-PROD-CHANGE-SET",
                                "StackName": projectName + "-PROD",
                                "TemplateConfiguration": "Build::config.json",
                                "TemplatePath": "Build::dummy.json",
                            }))
                        },
                        OutputArtifacts=[
                            codepipeline.OutputArtifacts(
                                Name="CreatePRODChangeSet",
                            )
                        ],
                        RunOrder="2",
                    ),
                ]
            ),

            codepipeline.Stages(
                Name="PROD-ApproveChangeSet",
                Actions=[
                    codepipeline.Actions(
                        Name="ApprovePRODChangeSet",
                        ActionTypeId=codepipeline.ActionTypeID(
                            Category="Approval",
                            Owner="AWS",
                            Version="1",
                            Provider="Manual",
                        ),
                        Configuration={
                            "NotificationArn": Ref(approve_topic),
                            "CustomData": "Approve deployment in production.",
                        },
                        RunOrder="1",
                    ),
                ]
            ),

            codepipeline.Stages(
                Name="PROD-ExecuteChangeSet",
                Actions=[
                    codepipeline.Actions(
                        Name="ExecutePRODChangeSet",
                        InputArtifacts=[
                            codepipeline.InputArtifacts(
                                Name="Build",
                            )
                        ],
                        ActionTypeId=codepipeline.ActionTypeID(
                            Category="Invoke",
                            Owner="AWS",
                            Version="1",
                            Provider="Lambda",
                        ),
                        Configuration={
                            "FunctionName": "lambda-cfn-provider",
                            "UserParameters": Sub(json.dumps({
                                "ActionMode": "CHANGE_SET_EXECUTE",
                                "ChangeSetName": projectName + "-PROD-CHANGE-SET",
                                "StackName": projectName + "-PROD",
                            }))
                        },
                        OutputArtifacts=[
                            codepipeline.OutputArtifacts(
                                Name="ExecutePRODChangeSet",
                            )
                        ],
                        RunOrder="1",
                    ),
                ]
            ),
        ]
    ))

    # OUTPUT section

    template.add_output([
        Output(
            "ArtifactStoreS3Bucket",
            Description="ResourceName of the S3 bucket containg the artifacts of the pipeline(s)",
            Value=Ref(artifact_store_s3_bucket),
            Export=Export(projectName + "-ArtifactS3Bucket"),
        ),
        Output(
            "ArtifactStoreS3BucketArn",
            Description="Arn of the S3 bucket containg the artifacts of the pipeline(s)",
            Value=GetAtt(artifact_store_s3_bucket, "Arn"),
            Export=Export(projectName + "-ArtifactS3BucketArn"),
        ),
        Output(
            "CodeBuildRole",
            Description="Logical name of the role that is used by the CodeBuild projects in the CodePipeline",
            Value=Ref(code_build_role),
            Export=Export(projectName + "-CodeBuildRole"),
        ),
        Output(
            "CloudFormationRoleArn",
            Description="Arn of the S3 bucket containing the artifacts of the pipeline(s)",
            Value=GetAtt(cloud_formation_role, "Arn"),
            Export=Export(projectName + "-CloudFormationRoleArn"),
        ),
        Output(
            "CodePipelineRoleArn",
            Description="Logical name of the role that is used by the CodePipeline",
            Value=GetAtt(code_pipeline_role, "Arn"),
            Export=Export(projectName + "-CodePipelineRoleArn"),
        )
    ])

    print(template.to_json())


if __name__ == '__main__':
    main()
