#!/usr/bin/env python3
"""
Test script to send DICOM files to the gateway

Usage:
    python send_dicom_test.py <dicom_file_or_directory>

Examples:
    python send_dicom_test.py sample.dcm
    python send_dicom_test.py /path/to/dicom/directory
"""

import sys
import os
from pathlib import Path
from pynetdicom import AE, debug_logger
from pynetdicom.sop_class import CTImageStorage, MRImageStorage, Verification
from pydicom import dcmread

# Enable debug logging
# debug_logger()

def send_dicom_file(file_path, host='localhost', port=11112, ae_title='VETIMAGE'):
    """
    Send a single DICOM file to the gateway

    Args:
        file_path: Path to DICOM file
        host: Gateway hostname
        port: Gateway port
        ae_title: Gateway AE title

    Returns:
        bool: True if successful
    """
    print(f"Sending {file_path} to {host}:{port} (AE: {ae_title})")

    try:
        # Read DICOM file
        ds = dcmread(file_path)
        print(f"  Patient ID: {ds.get('PatientID', 'N/A')}")
        print(f"  Study UID: {ds.get('StudyInstanceUID', 'N/A')[:40]}...")
        print(f"  Modality: {ds.get('Modality', 'N/A')}")

        # Create Application Entity
        ae = AE(ae_title='TEST_SCU')

        # Add presentation contexts based on SOP Class
        sop_class = ds.SOPClassUID
        ae.add_requested_context(sop_class)

        # Also add common storage contexts
        ae.add_requested_context(CTImageStorage)
        ae.add_requested_context(MRImageStorage)

        # Associate with gateway
        assoc = ae.associate(host, port, ae_title=ae_title)

        if assoc.is_established:
            print("  Association established ✓")

            # Send C-STORE request
            status = assoc.send_c_store(ds)

            if status:
                # Check the status
                if status.Status == 0x0000:
                    print(f"  C-STORE successful ✓ (Status: {status.Status:#06x})")
                    success = True
                else:
                    print(f"  C-STORE failed ✗ (Status: {status.Status:#06x})")
                    success = False
            else:
                print("  C-STORE failed: No response ✗")
                success = False

            # Release association
            assoc.release()
            print("  Association released ✓")

            return success
        else:
            print(f"  Failed to establish association ✗")
            return False

    except Exception as e:
        print(f"  Error: {str(e)} ✗")
        return False


def send_directory(directory_path, host='localhost', port=11112, ae_title='VETIMAGE'):
    """
    Send all DICOM files in a directory

    Args:
        directory_path: Path to directory containing DICOM files
        host: Gateway hostname
        port: Gateway port
        ae_title: Gateway AE title
    """
    directory = Path(directory_path)

    if not directory.is_dir():
        print(f"Error: {directory_path} is not a directory")
        return

    # Find all DICOM files
    dicom_files = []
    for ext in ['*.dcm', '*.dicom', '*.DCM', '*.DICOM']:
        dicom_files.extend(directory.glob(f'**/{ext}'))

    if not dicom_files:
        print(f"No DICOM files found in {directory_path}")
        return

    print(f"Found {len(dicom_files)} DICOM file(s)\n")

    success_count = 0
    fail_count = 0

    for file_path in dicom_files:
        if send_dicom_file(file_path, host, port, ae_title):
            success_count += 1
        else:
            fail_count += 1
        print()  # Blank line between files

    print("="* 60)
    print(f"Summary: {success_count} successful, {fail_count} failed")
    print("=" * 60)


def test_echo(host='localhost', port=11112, ae_title='VETIMAGE'):
    """
    Test gateway connectivity with C-ECHO

    Args:
        host: Gateway hostname
        port: Gateway port
        ae_title: Gateway AE title

    Returns:
        bool: True if successful
    """
    print(f"Testing C-ECHO to {host}:{port} (AE: {ae_title})")

    try:
        ae = AE(ae_title='TEST_ECHO')
        ae.add_requested_context(Verification)

        assoc = ae.associate(host, port, ae_title=ae_title)

        if assoc.is_established:
            print("  Association established ✓")

            status = assoc.send_c_echo()

            if status.Status == 0x0000:
                print(f"  C-ECHO successful ✓ (Status: {status.Status:#06x})")
                success = True
            else:
                print(f"  C-ECHO failed ✗ (Status: {status.Status:#06x})")
                success = False

            assoc.release()
            print("  Association released ✓")

            return success
        else:
            print("  Failed to establish association ✗")
            return False

    except Exception as e:
        print(f"  Error: {str(e)} ✗")
        return False


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Send DICOM files to VetImage gateway'
    )
    parser.add_argument(
        'path',
        nargs='?',
        help='Path to DICOM file or directory'
    )
    parser.add_argument(
        '--host',
        default='localhost',
        help='Gateway hostname (default: localhost)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=11112,
        help='Gateway port (default: 11112)'
    )
    parser.add_argument(
        '--aet',
        default='VETIMAGE',
        help='Gateway AE Title (default: VETIMAGE)'
    )
    parser.add_argument(
        '--echo',
        action='store_true',
        help='Test connectivity with C-ECHO only'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("VetImage DICOM Gateway Test Script")
    print("=" * 60)
    print()

    if args.echo:
        # Just test C-ECHO
        test_echo(args.host, args.port, args.aet)
        return

    if not args.path:
        print("Error: Please provide a file or directory path")
        parser.print_help()
        sys.exit(1)

    path = Path(args.path)

    if not path.exists():
        print(f"Error: Path does not exist: {args.path}")
        sys.exit(1)

    # Test connectivity first
    print("Step 1: Testing connectivity...\n")
    if not test_echo(args.host, args.port, args.aet):
        print("\n⚠️  C-ECHO failed. Check if gateway is running.")
        sys.exit(1)

    print("\n✓ Gateway is reachable\n")
    print("=" * 60)
    print("\nStep 2: Sending DICOM file(s)...\n")

    # Send file(s)
    if path.is_file():
        send_dicom_file(path, args.host, args.port, args.aet)
    elif path.is_dir():
        send_directory(path, args.host, args.port, args.aet)
    else:
        print(f"Error: Invalid path: {args.path}")
        sys.exit(1)


if __name__ == '__main__':
    main()
