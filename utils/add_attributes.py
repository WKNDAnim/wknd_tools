import maya.cmds as mc


def add_attributes_to_geo_meshes(asset_name, asset_info):

    meshes_in_asset = mc.listRelatives(f"{asset_name}|geo", ad=True, type='mesh', f=True)

    for mesh in meshes_in_asset:
        # First Clean possible old publish attributes
        try:
            mc.deleteAttr(f"{mesh}.GUS_relatedShader")
        except:
            pass
        add_attributes(mesh, asset_info)


def add_attributes(mesh, asset_info):

    # Get specific info for that mesh
    shading_engine = mc.listConnections(mesh, source=False, destination=True)[0]
    asset_info.update({"GUS_shading_grp": shading_engine})

    # Create Attributes
    for key in asset_info:

        if not mc.attributeQuery(key, node=mesh, exists=True):

            if type(asset_info[key]) == str:
                mc.addAttr(mesh, longName=key, dataType='string')
            elif type(asset_info[key])==int:
                mc.addAttr(mesh, longName=key, at='long')
            elif type(asset_info[key])==float:
                mc.addAttr(mesh, longName=key, at='double')
            elif type(asset_info[key])==bool:
                mc.addAttr(mesh, longName=key, at='bool')

        if type(asset_info[key]) == str:

            mc.setAttr(f"{mesh}.{key}", lock=False)
            mc.setAttr(f"{mesh}.{key}", asset_info[key], type='string')
            mc.setAttr(f"{mesh}.{key}", lock=True)

        else:

            mc.setAttr(f"{mesh}.{key}", lock=False)
            mc.setAttr(f"{mesh}.{key}", asset_info[key])
            mc.setAttr(f"{mesh}.{key}", lock=True)

"""

#USAGE EXAMPLE

asset_info = {'asset_name':'bancoCalle',
                'asset_type':'ELEM',
                'source_scene':'bancoCalle_scene_Model_v005',
                'sg_version_id': 12345,
                'difValue':0.8,
                'isRenderable':True}

"""