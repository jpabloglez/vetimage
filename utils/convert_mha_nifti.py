"""
Convert mha file to nifti format
"""
import argparse
import SimpleITK as sitk

def main(args):

    img = sitk.ReadImage(args.input_path)
    sitk.WriteImage(img, args.output_path)

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Convert mha file to nifti format")
    # Mha file path
    argparser.add_argument("-i", "--input_path", type=str, required=True, help="Path to the directory containing data.mha")
    argparser.add_argument("-o", "--output_path", type=str, required=True, help="Path to the directory containing data.nii")
    args = argparser.parse_args()
    print("Arguments:", args    )
    main(args)