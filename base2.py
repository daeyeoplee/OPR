import blenderproc as bproc
import bpy
import random
import os
import math
import time
from mathutils import Euler
from pathlib import Path

# input obj_name
# eg. "FT"
# duplicate with scale(10,10,10) and random location, random rotation


def duplicate(obj, times):
    # copy name = {Choco Name}00n <- FT001
    copy_list = list()
    for i in range(0, times):
        obj_copy = obj.duplicate()
        obj_copy.set_origin(mode="CENTER_OF_MASS")
        obj_copy.set_location([random.uniform(-3, 3),
                             random.uniform(-3, 3), random.uniform(3, 5)])
        obj_copy.set_rotation_euler([random.random() * 2 * math.pi, random.random() * 2 * math.pi, random.random() * 2 * math.pi])
        # set as an active object
        obj_copy.enable_rigidbody(active=True, collision_margin=0.04)
        copy_list = copy_list + [obj_copy]
        # obj_copy['category_id'] = bpy.data.objects[obj_name]['category_id']
        obj_copy.set_cp("category_id", obj.get_cp("category_id"))
    return copy_list

# input obj_name
# eg. "FT"


def randomly_rotate(obj_name):
    obj_to_rotate = bpy.context.scene.objects[obj_name]
    random_rot = (random.random() * 2 * math.pi, random.random()
                  * 2 * math.pi, random.random() * 2 * math.pi)
    obj_to_rotate.rotation_euler = Euler(random_rot, 'XYZ')


def setting(objs):
    copy_list = list()
    for obj in objs:
        copy_list = copy_list + duplicate(obj, random.randrange(2, 6))
    return copy_list


def delete(copies):
    if bpy.context.object.mode == 'EDIT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    # select the object
    for copied in copies:
        bpy.data.objects[copied.name].select_set(True)
        # delete all selected objects
        bpy.ops.object.delete()


bproc.init()

# Load objects
print("Loading Cam, Light, Meshes")
objs = bproc.loader.load_obj("C:/Users/teala/Desktop/Object-Picking-Robot/base.obj")
print("Loaded")


matrix_world = bproc.math.build_transformation_mat((0, 0, 10), (0, 0, 0))
bproc.camera.add_camera_pose(matrix_world)
bproc.camera.set_resolution(512, 512)

for obj in objs:
    if obj.get_name() == "Base":
        base = obj
    elif obj.get_name() == "FT":
        ft = obj
    elif obj.get_name() == "GR":
        gr = obj
    elif obj.get_name() == "HB":
        hb = obj
    elif obj.get_name() == "GY":
        gy = obj
    elif obj.get_name() == "Camera":
        camera = obj

base.enable_rigidbody(active=False, collision_shape="MESH", collision_margin=0.3)

light = bproc.types.Light()
light.set_energy(2000)
light.set_location([0, 0, 8])

Choco_list = [ft, gr, gy, hb]
ft.set_cp("category_id", 1)
gr.set_cp("category_id", 2)
gy.set_cp("category_id", 3)
hb.set_cp("category_id", 4)
base.set_cp("category_id", 0)

obj_renders_per_split = [('train', 3), ('val', 0), ('test', 0)]
total_render_count = sum([r[1] for r in obj_renders_per_split])
output_path = Path('C:/data/choco')

# Tracks the starting image index for each object loop
start_idx = 0
start_time = time.time()

# Real Rendering
for split_name, renders_per_split in obj_renders_per_split:
    print(
        f"\nStarting split: {split_name} | Total renders: {renders_per_split}")
    print("="*40)

    for i in range(start_idx, start_idx + renders_per_split):
        # Setting returns copied obj list
        copies = setting(Choco_list)
        
        # Log status
        print(f'Rendering image {i + 1} of {total_render_count}')
        seconds_per_render = (time.time() - start_time) / (i + 1)
        seconds_remaining = seconds_per_render * (total_render_count - i - 1)
        print(
            f'Estimated time remaining: {time.strftime("%H:%M:%S", time.gmtime(seconds_remaining))}')

        # Physics Simulation part
        bpy.context.scene.frame_end = 70
        bpy.ops.screen.frame_jump(end=False)
        for t in range(70):
            bpy.context.scene.frame_set(t)

        # Deselect all objects
        bpy.ops.object.select_all(action="DESELECT")

        for o in copies:
            bpy.data.objects[o.get_name()].select_set(True)
        bpy.ops.transform.translate(value=(
            0, 0, 0), orient_axis_ortho='X', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)))
        bpy.context.scene.frame_end = 1
        bpy.ops.screen.frame_jump(end=False)

        # Update file path and render
        bpy.context.scene.render.filepath = str(
            output_path / split_name / f'{str(i).zfill(6)}.png')
        # bpy.ops.render.render(write_still=True)

        #for j, obj in enumerate(copies):
            # obj.set_cp("category_id", j+1)
            # obj['category_id'] = j+1

        print("seg Rendering")
        bproc.renderer.enable_normals_output()
        data = bproc.renderer.render()
        seg_data = bproc.renderer.render_segmap(
            map_by=["instance", "class", "name"])

        # colors key error
        print(seg_data.keys())
        print("Writing COCO")
        bproc.writer.write_coco_annotations(os.path.join(output_path, split_name, 'coco_data'), instance_segmaps=seg_data["instance_segmaps"],
                                            instance_attribute_maps=seg_data["instance_attribute_maps"], colors=data["colors"], color_file_format="JPEG")
        print("COCO finished")

        # delete Copied Chocos
        # delete(copies)
        for obj in copies:
            obj.delete()

    start_idx += renders_per_split
