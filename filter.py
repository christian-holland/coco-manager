import json
from pathlib import Path
import random

class CocoFilter():
    """ Filters the COCO dataset
    """
    def _process_info(self):
        if 'info' in self.coco:
            self.info = self.coco['info']
        else:
            self.info = []
        
    def _process_licenses(self):
        if 'licenses' in self.coco:
            self.licenses = self.coco['licenses']
        else:
            self.licenses = []
        
    def _process_categories(self):
        self.categories = dict()
        self.super_categories = dict()
        self.category_set = set()

        for category in self.coco['categories']:
            cat_id = category['id']
            super_category = category['supercategory']
            
            # Add category to categories dict
            if cat_id not in self.categories:
                self.categories[cat_id] = category
                self.category_set.add(category['name'])
            else:
                print(f'ERROR: Skipping duplicate category id: {category}')
            
            # Add category id to the super_categories dict
            if super_category not in self.super_categories:
                self.super_categories[super_category] = {cat_id}
            else:
                self.super_categories[super_category] |= {cat_id} # e.g. {1, 2, 3} |= {4} => {1, 2, 3, 4}

    def _process_images(self):
        self.images = dict()
        for image in self.coco['images']:
            image_id = image['id']
            if image_id not in self.images:
                self.images[image_id] = image
            else:
                print(f'ERROR: Skipping duplicate image id: {image}')
                
    def _process_segmentations(self):
        self.segmentations = dict()
        for segmentation in self.coco['annotations']:
            image_id = segmentation['image_id']
            if image_id not in self.segmentations:
                self.segmentations[image_id] = []
            self.segmentations[image_id].append(segmentation)

    def _filter_categories(self):
        """ Find category ids matching args
            Create mapping from original category id to new category id
            Create new collection of categories
        """
        print(self.filter_categories)
        missing_categories = set(self.filter_categories) - self.category_set
        if len(missing_categories) > 0:
            print(f'Did not find categories: {missing_categories}')
            should_continue = input('Continue? (y/n) ').lower()
            if should_continue != 'y' and should_continue != 'yes':
                print('Quitting early.')
                quit()

        self.new_category_map = dict()
        new_id = 1
        for key, item in self.categories.items():
            if item['name'] in self.filter_categories:
                self.new_category_map[key] = new_id
                new_id += 1

        self.new_categories = []
        for original_cat_id, new_id in self.new_category_map.items():
            new_category = dict(self.categories[original_cat_id])
            new_category['id'] = new_id
            self.new_categories.append(new_category)

    def _filter_annotations(self):
        """ Create new collection of annotations matching category ids
            Keep track of image ids matching annotations
        """
        self.new_segmentations = []
        self.new_image_ids = set()
        for image_id, segmentation_list in self.segmentations.items():
            for segmentation in segmentation_list:
                original_seg_cat = segmentation['category_id']
                if original_seg_cat in self.new_category_map.keys():
                    new_segmentation = dict(segmentation)
                    new_segmentation['category_id'] = self.new_category_map[original_seg_cat]
                    self.new_segmentations.append(new_segmentation)
                    self.new_image_ids.add(image_id)

    def _filter_images(self):
        """ Create new collection of images
        """
        self.new_images = []
        for image_id in self.new_image_ids:
            self.new_images.append(self.images[image_id])

    def main(self, args):
        # Open json
        self.input_json_path = Path(args.input_json)
        self.output_json_path = Path(args.output_json)
        self.val_json_path = Path(args.val_json)
        self.filter_categories = args.categories

        # Verify input path exists
        if not self.input_json_path.exists():
            print('Input json path not found.')
            print('Quitting early.')
            quit()

        # Verify output path does not already exist
        if self.output_json_path.exists():
            should_continue = input('Output path already exists. Overwrite? (y/n) ').lower()
            if should_continue != 'y' and should_continue != 'yes':
                print('Quitting early.')
                quit()
        
        # Load the json
        print('Loading json file...')
        with open(self.input_json_path) as json_file:
            self.coco = json.load(json_file)
        
        # Process the json
        print('Processing input json...')
        self._process_info()
        self._process_licenses()
        self._process_categories()
        self._process_images()
        self._process_segmentations()

        # Filter to specific categories
        print('Filtering...')
        self._filter_categories()
        self._filter_annotations()
        self._filter_images()

        if args.val_json:
            with open("val_names.json") as json_file:
                self.val_names = json.load(json_file)
                val_images = [im for im in self.new_images if (im["path"].split("/")[-1] in self.val_names)]
                val_ids = [im["id"] for im in val_images]
                val_annotations = [seg for seg in self.new_segmentations if seg["image_id"] in val_ids]
                val_json = {
                    'info': self.info,
                    'licenses': self.licenses,
                    'images': val_images,
                    'annotations': val_annotations,
                    'categories': self.new_categories
                }
                print('Saving new val json file...')
                with open(self.val_json_path, 'w+') as output_file:
                    json.dump(val_json, output_file)

                train_images = [im for im in self.new_images if (im["path"].split("/")[-1] not in self.val_names)]
                train_ids = [im["id"] for im in train_images]
                train_annotations = [seg for seg in self.new_segmentations if seg["image_id"] in train_ids]

                train_json = {
                    'info': self.info,
                    'licenses': self.licenses,
                    'images': train_images,
                    'annotations': train_annotations,
                    'categories': self.new_categories
                }

        else:
            # Build new JSON
            train_json = {
                'info': self.info,
                'licenses': self.licenses,
                'images': self.new_images,
                'annotations': self.new_segmentations,
                'categories': self.new_categories
            }


        # imnames = [im["path"].split("/")[-1] for im in self.new_images]
        # random.shuffle(imnames)
        # val_names = imnames[:30]
        # with open("val_names.json", 'w+') as output_file:
        #     json.dump(val_names, output_file)
        # exit()

        # Write the JSON to a file
        print('Saving new json file...')
        with open(self.output_json_path, 'w+') as output_file:
            json.dump(train_json, output_file)

        print('Filtered json saved.')

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Filter COCO JSON: "
    "Filters a COCO Instances JSON file to only include specified categories. "
    "This includes images, and annotations. Does not modify 'info' or 'licenses'.")
    
    parser.add_argument("-i", "--input_json", dest="input_json",
        help="path to a json file in coco format")
    parser.add_argument("-o", "--output_json", dest="output_json",
        help="path to save the output json")
    parser.add_argument("-v", "--val_json", dest="val_json", default="",
        help="path to save the val output json")
    parser.add_argument("-c", "--categories", nargs='+', dest="categories",
        help="List of category names separated by spaces, e.g. -c person dog bicycle")

    args = parser.parse_args()

    cf = CocoFilter()
    cf.main(args)
