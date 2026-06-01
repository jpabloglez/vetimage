/**
 * Cornerstone Initialization Utilities
 *
 * Configure Cornerstone libraries and image loaders for DICOM viewing
 */

import * as cornerstone from 'cornerstone-core';
import * as cornerstoneTools from 'cornerstone-tools';
import cornerstoneWADOImageLoader from 'cornerstone-wado-image-loader';
import * as dicomParser from 'dicom-parser';
import Hammer from 'hammerjs';
import * as cornerstoneMath from 'cornerstone-math';
import { apiClient } from './api';

let initialized = false;

/**
 * Initialize Cornerstone libraries (call once on app startup)
 */
export function initializeCornerstone() {
  if (initialized) {
    console.log('Cornerstone already initialized');
    return;
  }

  console.log('Initializing Cornerstone...');

  // Set external dependencies
  cornerstoneTools.external.cornerstone = cornerstone;
  cornerstoneTools.external.Hammer = Hammer;
  cornerstoneTools.external.cornerstoneMath = cornerstoneMath;
  cornerstoneWADOImageLoader.external.cornerstone = cornerstone;
  cornerstoneWADOImageLoader.external.dicomParser = dicomParser;

  // Configure WADO Image Loader
  cornerstoneWADOImageLoader.configure({
    // Use web workers for image decoding (better performance)
    useWebWorkers: true,
    decodeConfig: {
      convertFloatPixelDataToInt: false,
      use16BitDataType: true,
    },
    // Add authentication headers to requests
    beforeSend: (xhr: XMLHttpRequest) => {
      const token = apiClient.getAccessToken();
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }
      console.log('Loading DICOM image from:', xhr.url);
    },
  });

  // Initialize web workers for image loading
  const config = {
    maxWebWorkers: navigator.hardwareConcurrency || 4,
    startWebWorkersOnDemand: true,
    taskConfiguration: {
      decodeTask: {
        initializeCodecsOnStartup: false,
        usePDFJS: false,
      },
    },
  };

  cornerstoneWADOImageLoader.webWorkerManager.initialize(config);

  // Initialize cornerstone tools
  cornerstoneTools.init({
    mouseEnabled: true,
    touchEnabled: true,
    globalToolSyncEnabled: false,
    showSVGCursors: true,
  });

  // Register custom image loader for HTTP URLs (JPEG/PNG from backend)
  // Do this AFTER tools init
  try {
    cornerstone.registerImageLoader('http', loadHttpImage);
    cornerstone.registerImageLoader('https', loadHttpImage);
    console.log('Custom HTTP image loaders registered');
  } catch (err) {
    console.error('Failed to register image loaders:', err);
  }

  initialized = true;
  console.log('Cornerstone initialized successfully');
}

/**
 * Custom image loader for HTTP/HTTPS URLs with authentication
 * Loads JPEG/PNG images from the backend with auth headers
 */
function loadHttpImage(imageId: string): any {
  console.log('Custom HTTP loader called for:', imageId);

  const promise = new Promise((resolve, reject) => {
    console.log('Promise constructor running');

    const image = new Image();
    image.crossOrigin = 'use-credentials';

    // Extract URL from imageId
    const url = imageId;

    // Add auth headers via XMLHttpRequest
    const xhr = new XMLHttpRequest();
    xhr.open('GET', url);
    xhr.responseType = 'blob';

    // Add authentication
    const token = apiClient.getAccessToken();
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }

    xhr.onload = () => {
      console.log('XHR loaded, status:', xhr.status);
      if (xhr.status === 200) {
        const urlCreator = window.URL || window.webkitURL;
        const imageUrl = urlCreator.createObjectURL(xhr.response);

        image.onload = () => {
          console.log('Image element loaded successfully');
          const imageObject = {
            imageId,
            minPixelValue: 0,
            maxPixelValue: 255,
            slope: 1.0,
            intercept: 0,
            windowCenter: 127,
            windowWidth: 256,
            render: cornerstone.renderWebImage,
            getPixelData: () => image,
            rows: image.naturalHeight,
            columns: image.naturalWidth,
            height: image.naturalHeight,
            width: image.naturalWidth,
            color: true,
            rgba: false,
            columnPixelSpacing: 1.0,
            rowPixelSpacing: 1.0,
            invert: false,
            sizeInBytes: image.width * image.height * 4,
          };

          resolve(imageObject);
          urlCreator.revokeObjectURL(imageUrl);
        };

        image.onerror = () => {
          console.error('Image element failed to load');
          urlCreator.revokeObjectURL(imageUrl);
          reject(new Error('Failed to load image'));
        };

        image.src = imageUrl;
      } else {
        console.error('XHR failed with status:', xhr.status);
        reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
      }
    };

    xhr.onerror = () => {
      console.error('XHR network error');
      reject(new Error('Network error loading image'));
    };

    console.log('Sending XHR request');
    xhr.send();
  });

  console.log('Returning promise:', promise);
  return promise;
}

/**
 * Clean up Cornerstone resources
 */
export function cleanupCornerstone() {
  try {
    // Disable all enabled elements
    const enabledElements = cornerstone.getEnabledElements();
    enabledElements.forEach((enabledElement) => {
      try {
        cornerstone.disable(enabledElement.element);
      } catch (err) {
        console.warn('Error disabling element:', err);
      }
    });

    // Clear image cache
    cornerstone.imageCache.purgeCache();

    console.log('Cornerstone cleaned up');
  } catch (err) {
    console.error('Error during Cornerstone cleanup:', err);
  }
}

/**
 * Enable a DOM element for Cornerstone rendering
 */
export function enableElement(element: HTMLDivElement): void {
  try {
    const enabled = cornerstone.getEnabledElement(element);
    if (!enabled) {
      cornerstone.enable(element);
      console.log('Element enabled for Cornerstone');
    }
  } catch (err) {
    // Element not enabled yet, enable it
    cornerstone.enable(element);
    console.log('Element enabled for Cornerstone');
  }
}

/**
 * Disable a DOM element
 */
export function disableElement(element: HTMLDivElement): void {
  try {
    cornerstone.disable(element);
    console.log('Element disabled');
  } catch (err) {
    console.warn('Error disabling element:', err);
  }
}

/**
 * Generate image ID for Cornerstone
 *
 * Note: Our backend returns JPEG/PNG (not raw DICOM), so we use a regular HTTP URL
 */
export function generateImageId(
  studyUID: string,
  seriesUID: string,
  sopUID: string,
  frameNumber: number = 1
): string {
  const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:3080';

  // WADO-RS URL format (returns JPEG/PNG from backend)
  const wadoUrl = `${baseUrl}/api/dicom/dicom-web/studies/${studyUID}/series/${seriesUID}/instances/${sopUID}/frames/${frameNumber}`;

  // For JPEG/PNG images, use http: scheme (not wadouri:)
  return wadoUrl;
}

/**
 * Add and activate basic viewing tools
 */
export function addBasicTools(element: HTMLDivElement): void {
  // Add tools
  const WwwcTool = cornerstoneTools.WwwcTool;
  const ZoomTool = cornerstoneTools.ZoomTool;
  const PanTool = cornerstoneTools.PanTool;
  const StackScrollMouseWheelTool = cornerstoneTools.StackScrollMouseWheelTool;

  cornerstoneTools.addTool(WwwcTool);
  cornerstoneTools.addTool(ZoomTool);
  cornerstoneTools.addTool(PanTool);
  cornerstoneTools.addTool(StackScrollMouseWheelTool);

  // Set active tools
  cornerstoneTools.setToolActive('Wwwc', { mouseButtonMask: 1 }); // Left click for window/level
  cornerstoneTools.setToolActive('Zoom', { mouseButtonMask: 2 }); // Middle click for zoom
  cornerstoneTools.setToolActive('Pan', { mouseButtonMask: 4 });  // Right click for pan
  cornerstoneTools.setToolActive('StackScrollMouseWheel', {}); // Mouse wheel for scrolling

  console.log('Basic tools added and activated');
}

/**
 * Load and display an image
 * Directly loads JPEG/PNG from backend and renders as web image
 */
export async function loadAndDisplayImage(
  element: HTMLDivElement,
  imageId: string
): Promise<void> {
  try {
    console.log('Loading image:', imageId);

    // Load image directly with authentication
    const imageObject = await loadImageWithAuth(imageId);

    // Display image
    cornerstone.displayImage(element, imageObject);

    console.log('Image displayed successfully');
  } catch (error) {
    console.error('Failed to load and display image:', error);
    throw error;
  }
}

/**
 * Load image with authentication and create Cornerstone image object
 */
async function loadImageWithAuth(imageUrl: string): Promise<any> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('GET', imageUrl);
    xhr.responseType = 'blob';

    // Add authentication
    const token = apiClient.getAccessToken();
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }

    xhr.onload = () => {
      if (xhr.status === 200) {
        const urlCreator = window.URL || window.webkitURL;
        const blobUrl = urlCreator.createObjectURL(xhr.response);

        const image = new Image();
        image.onload = () => {
          // Create Cornerstone image object for web images
          const imageObject = {
            imageId: imageUrl,
            minPixelValue: 0,
            maxPixelValue: 255,
            slope: 1.0,
            intercept: 0,
            windowCenter: 127,
            windowWidth: 256,
            render: cornerstone.renderWebImage,
            getImage: () => image,  // Required by renderWebImage
            getPixelData: () => image,
            rows: image.naturalHeight,
            columns: image.naturalWidth,
            height: image.naturalHeight,
            width: image.naturalWidth,
            color: true,
            rgba: false,
            columnPixelSpacing: 1.0,
            rowPixelSpacing: 1.0,
            invert: false,
            sizeInBytes: image.width * image.height * 4,
          };

          urlCreator.revokeObjectURL(blobUrl);
          resolve(imageObject);
        };

        image.onerror = () => {
          urlCreator.revokeObjectURL(blobUrl);
          reject(new Error('Failed to load image'));
        };

        image.src = blobUrl;
      } else {
        reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
      }
    };

    xhr.onerror = () => {
      reject(new Error('Network error loading image'));
    };

    xhr.send();
  });
}

/**
 * Reset viewport to default view
 */
export function resetViewport(element: HTMLDivElement): void {
  try {
    cornerstone.reset(element);
    console.log('Viewport reset');
  } catch (err) {
    console.error('Error resetting viewport:', err);
  }
}

/**
 * Fit image to window
 */
export function fitToWindow(element: HTMLDivElement): void {
  try {
    cornerstone.fitToWindow(element);
    console.log('Fitted to window');
  } catch (err) {
    console.error('Error fitting to window:', err);
  }
}

// Export cornerstone and tools for direct access if needed
export { cornerstone, cornerstoneTools };
