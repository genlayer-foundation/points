<script>
  import { onMount, onDestroy } from 'svelte';
  
  let { 
    image, 
    aspectRatio = 1, 
    onCrop = () => {}, 
    onCancel = () => {},
    title = "Crop Image"
  } = $props();
  
  let canvas = $state(null);
  let cropBox = $state({ x: 0, y: 0, width: 100, height: 100 });
  let imageElement = $state(null);
  let isDragging = $state(false);
  let isResizing = $state(false);
  let resizeHandle = $state('');
  let dragStart = $state({ x: 0, y: 0 });
  let containerRef;
  let canvasRef;
  let imageLoaded = $state(false);
  let cursorStyle = $state('default');
  let imageBounds = $state({ x: 0, y: 0, width: 0, height: 0 });
  let hoveredHandle = $state('');
  let showDimensions = $state(false);
  
  onMount(() => {
    loadImage();
    // Add global mouse up listener to handle mouse up outside canvas
    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('touchend', handleTouchEnd);
    return () => {
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('touchend', handleTouchEnd);
    };
  });
  
  function loadImage() {
    const img = new Image();
    img.onload = () => {
      imageElement = img;
      imageLoaded = true;
      initializeCropBox();
      drawCanvas();
    };
    img.src = image;
  }
  
  function calculateImageBounds() {
    if (!imageElement || !containerRef) return;
    
    const containerRect = containerRef.getBoundingClientRect();
    const scale = Math.min(
      containerRect.width / imageElement.width,
      containerRect.height / imageElement.height
    );
    
    const displayWidth = imageElement.width * scale;
    const displayHeight = imageElement.height * scale;
    const offsetX = (containerRect.width - displayWidth) / 2;
    const offsetY = (containerRect.height - displayHeight) / 2;
    
    imageBounds = {
      x: offsetX,
      y: offsetY,
      width: displayWidth,
      height: displayHeight
    };
    
    return imageBounds;
  }
  
  function initializeCropBox() {
    if (!imageElement || !containerRef) return;
    
    const bounds = calculateImageBounds();
    
    // Initialize crop box to center with 80% of image size
    const cropSize = Math.min(bounds.width, bounds.height) * 0.8;
    const cropWidth = cropSize;
    const cropHeight = cropSize / aspectRatio;
    
    // Ensure crop box fits within image bounds
    const finalWidth = Math.min(cropWidth, bounds.width * 0.9);
    const finalHeight = Math.min(cropHeight, bounds.height * 0.9);
    
    cropBox = {
      x: bounds.x + (bounds.width - finalWidth) / 2,
      y: bounds.y + (bounds.height - finalHeight) / 2,
      width: finalWidth,
      height: finalHeight
    };
  }
  
  function drawCanvas() {
    if (!canvasRef || !imageElement || !imageLoaded) return;
    
    const ctx = canvasRef.getContext('2d');
    const containerRect = containerRef.getBoundingClientRect();
    
    // Clear canvas
    ctx.clearRect(0, 0, canvasRef.width, canvasRef.height);
    
    // Calculate image bounds
    const bounds = calculateImageBounds();
    
    // Draw image
    ctx.drawImage(imageElement, bounds.x, bounds.y, bounds.width, bounds.height);
    
    // Draw dark overlay outside crop area
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    ctx.fillRect(0, 0, canvasRef.width, canvasRef.height);
    
    // Clear crop area (show original image)
    ctx.save();
    ctx.globalCompositeOperation = 'destination-out';
    ctx.fillRect(cropBox.x, cropBox.y, cropBox.width, cropBox.height);
    ctx.restore();
    
    // Redraw the image in crop area only
    ctx.save();
    ctx.beginPath();
    ctx.rect(cropBox.x, cropBox.y, cropBox.width, cropBox.height);
    ctx.clip();
    ctx.drawImage(imageElement, bounds.x, bounds.y, bounds.width, bounds.height);
    ctx.restore();
    
    // Draw crop box border
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2;
    ctx.strokeRect(cropBox.x, cropBox.y, cropBox.width, cropBox.height);
    
    // Draw grid lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 1;
    
    // Vertical lines
    const thirdWidth = cropBox.width / 3;
    for (let i = 1; i < 3; i++) {
      ctx.beginPath();
      ctx.moveTo(cropBox.x + thirdWidth * i, cropBox.y);
      ctx.lineTo(cropBox.x + thirdWidth * i, cropBox.y + cropBox.height);
      ctx.stroke();
    }
    
    // Horizontal lines
    const thirdHeight = cropBox.height / 3;
    for (let i = 1; i < 3; i++) {
      ctx.beginPath();
      ctx.moveTo(cropBox.x, cropBox.y + thirdHeight * i);
      ctx.lineTo(cropBox.x + cropBox.width, cropBox.y + thirdHeight * i);
      ctx.stroke();
    }
    
    // Draw resize handles
    const handleSize = 10;
    const handles = [
      { x: cropBox.x, y: cropBox.y, cursor: 'nw-resize', type: 'nw' },
      { x: cropBox.x + cropBox.width, y: cropBox.y, cursor: 'ne-resize', type: 'ne' },
      { x: cropBox.x, y: cropBox.y + cropBox.height, cursor: 'sw-resize', type: 'sw' },
      { x: cropBox.x + cropBox.width, y: cropBox.y + cropBox.height, cursor: 'se-resize', type: 'se' }
    ];
    
    handles.forEach(handle => {
      // Highlight hovered handle
      if (hoveredHandle === handle.type) {
        ctx.fillStyle = '#4a90e2';
        ctx.fillRect(handle.x - handleSize/2 - 2, handle.y - handleSize/2 - 2, handleSize + 4, handleSize + 4);
      }
      
      ctx.fillStyle = '#fff';
      ctx.fillRect(handle.x - handleSize/2, handle.y - handleSize/2, handleSize, handleSize);
      
      // Draw border for handles
      ctx.strokeStyle = '#333';
      ctx.lineWidth = 1;
      ctx.strokeRect(handle.x - handleSize/2, handle.y - handleSize/2, handleSize, handleSize);
    });
    
    // Show dimensions while resizing
    if (showDimensions && (isResizing || isDragging)) {
      ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
      ctx.fillRect(cropBox.x, cropBox.y - 25, 100, 20);
      ctx.fillStyle = '#fff';
      ctx.font = '12px sans-serif';
      ctx.fillText(`${Math.round(cropBox.width)} x ${Math.round(cropBox.height)}`, cropBox.x + 5, cropBox.y - 10);
    }
  }
  
  function getCursorForPosition(x, y) {
    const handleSize = 10; // Match the visual handle size from drawCanvas
    const buffer = 3; // Small buffer for easier clicking
    const halfSize = handleSize / 2 + buffer;
    
    // Check if mouse is within the actual drawn handle rectangle
    // Handles are drawn centered on the corner positions
    
    // Northwest corner
    if (x >= cropBox.x - halfSize && x <= cropBox.x + halfSize &&
        y >= cropBox.y - halfSize && y <= cropBox.y + halfSize) {
      return 'nw-resize';
    }
    
    // Northeast corner
    if (x >= cropBox.x + cropBox.width - halfSize && x <= cropBox.x + cropBox.width + halfSize &&
        y >= cropBox.y - halfSize && y <= cropBox.y + halfSize) {
      return 'ne-resize';
    }
    
    // Southwest corner
    if (x >= cropBox.x - halfSize && x <= cropBox.x + halfSize &&
        y >= cropBox.y + cropBox.height - halfSize && y <= cropBox.y + cropBox.height + halfSize) {
      return 'sw-resize';
    }
    
    // Southeast corner
    if (x >= cropBox.x + cropBox.width - halfSize && x <= cropBox.x + cropBox.width + halfSize &&
        y >= cropBox.y + cropBox.height - halfSize && y <= cropBox.y + cropBox.height + halfSize) {
      return 'se-resize';
    }
    
    // Check if inside crop box
    if (x >= cropBox.x && x <= cropBox.x + cropBox.width && y >= cropBox.y && y <= cropBox.y + cropBox.height) {
      return 'move';
    }
    
    return 'default';
  }
  
  function getHoveredHandle(x, y) {
    const handleSize = 10; // Match the visual handle size from drawCanvas
    const buffer = 3; // Small buffer for easier clicking
    const halfSize = handleSize / 2 + buffer;
    
    // Check if mouse is within the actual drawn handle rectangle
    // Handles are drawn centered on the corner positions
    
    // Northwest corner
    if (x >= cropBox.x - halfSize && x <= cropBox.x + halfSize &&
        y >= cropBox.y - halfSize && y <= cropBox.y + halfSize) {
      return 'nw';
    }
    
    // Northeast corner
    if (x >= cropBox.x + cropBox.width - halfSize && x <= cropBox.x + cropBox.width + halfSize &&
        y >= cropBox.y - halfSize && y <= cropBox.y + halfSize) {
      return 'ne';
    }
    
    // Southwest corner
    if (x >= cropBox.x - halfSize && x <= cropBox.x + halfSize &&
        y >= cropBox.y + cropBox.height - halfSize && y <= cropBox.y + cropBox.height + halfSize) {
      return 'sw';
    }
    
    // Southeast corner
    if (x >= cropBox.x + cropBox.width - halfSize && x <= cropBox.x + cropBox.width + halfSize &&
        y >= cropBox.y + cropBox.height - halfSize && y <= cropBox.y + cropBox.height + halfSize) {
      return 'se';
    }
    
    return '';
  }
  
  function constrainCropBox(box) {
    const bounds = imageBounds;
    
    // First, ensure minimum size while maintaining aspect ratio
    const minWidth = 50;
    const minHeight = minWidth / aspectRatio;
    
    if (box.width < minWidth || box.height < minHeight) {
      box.width = minWidth;
      box.height = minHeight;
    }
    
    // Check if the box exceeds image bounds and maintain aspect ratio
    const maxWidth = bounds.width;
    const maxHeight = bounds.height;
    
    // Calculate what the dimensions would be if we're limited by width or height
    const widthLimited = {
      width: Math.min(box.width, maxWidth),
      height: Math.min(box.width, maxWidth) / aspectRatio
    };
    
    const heightLimited = {
      width: Math.min(box.height, maxHeight) * aspectRatio,
      height: Math.min(box.height, maxHeight)
    };
    
    // Choose the constraint that results in the smaller box (to fit within bounds)
    if (widthLimited.width <= maxWidth && widthLimited.height <= maxHeight) {
      // Width is the limiting factor
      if (heightLimited.width <= maxWidth && heightLimited.height <= maxHeight) {
        // Both fit, choose the one closer to original request
        if (Math.abs(box.width - widthLimited.width) <= Math.abs(box.height - heightLimited.height)) {
          box.width = widthLimited.width;
          box.height = widthLimited.height;
        } else {
          box.width = heightLimited.width;
          box.height = heightLimited.height;
        }
      } else {
        // Only width-limited fits
        box.width = widthLimited.width;
        box.height = widthLimited.height;
      }
    } else if (heightLimited.width <= maxWidth && heightLimited.height <= maxHeight) {
      // Only height-limited fits
      box.width = heightLimited.width;
      box.height = heightLimited.height;
    } else {
      // Need to find the maximum size that fits
      if (maxWidth / aspectRatio <= maxHeight) {
        // Width is limiting
        box.width = maxWidth;
        box.height = maxWidth / aspectRatio;
      } else {
        // Height is limiting
        box.height = maxHeight;
        box.width = maxHeight * aspectRatio;
      }
    }
    
    // Constrain position - left and top edges
    box.x = Math.max(bounds.x, box.x);
    box.y = Math.max(bounds.y, box.y);
    
    // Constrain position - right and bottom edges
    // If the box would extend beyond the right edge, pull it back
    if (box.x + box.width > bounds.x + bounds.width) {
      box.x = bounds.x + bounds.width - box.width;
    }
    
    // If the box would extend beyond the bottom edge, pull it back
    if (box.y + box.height > bounds.y + bounds.height) {
      box.y = bounds.y + bounds.height - box.height;
    }
    
    // Final safety check - ensure we're completely within bounds
    box.x = Math.max(bounds.x, Math.min(bounds.x + bounds.width - box.width, box.x));
    box.y = Math.max(bounds.y, Math.min(bounds.y + bounds.height - box.height, box.y));
    
    return box;
  }
  
  function handleMouseDown(event) {
    const rect = canvasRef.getBoundingClientRect();
    // Scale mouse coordinates to match canvas internal coordinates
    const scaleX = canvasRef.width / rect.width;
    const scaleY = canvasRef.height / rect.height;
    const x = (event.clientX - rect.left) * scaleX;
    const y = (event.clientY - rect.top) * scaleY;
    
    // Only allow interaction within image bounds
    if (x < imageBounds.x || x > imageBounds.x + imageBounds.width ||
        y < imageBounds.y || y > imageBounds.y + imageBounds.height) {
      return;
    }
    
    const cursor = getCursorForPosition(x, y);
    
    if (cursor.includes('resize')) {
      isResizing = true;
      resizeHandle = cursor.replace('-resize', '');
      dragStart = { x, y, originalBox: { ...cropBox } };
      showDimensions = true;
    } else if (cursor === 'move') {
      isDragging = true;
      dragStart = { x: x - cropBox.x, y: y - cropBox.y };
      showDimensions = true;
    }
  }
  
  function handleMouseMove(event) {
    const rect = canvasRef.getBoundingClientRect();
    // Scale mouse coordinates to match canvas internal coordinates
    const scaleX = canvasRef.width / rect.width;
    const scaleY = canvasRef.height / rect.height;
    const x = (event.clientX - rect.left) * scaleX;
    const y = (event.clientY - rect.top) * scaleY;
    
    // Update cursor and hover state
    if (!isDragging && !isResizing) {
      cursorStyle = getCursorForPosition(x, y);
      hoveredHandle = getHoveredHandle(x, y);
      drawCanvas();
    }
    
    if (isDragging) {
      let newBox = { ...cropBox };
      newBox.x = x - dragStart.x;
      newBox.y = y - dragStart.y;
      
      cropBox = constrainCropBox(newBox);
      drawCanvas();
    } else if (isResizing) {
      let newBox = { ...cropBox };
      const originalBox = dragStart.originalBox;
      
      // Calculate maximum dimensions that would fit within image bounds
      const maxPossibleWidth = imageBounds.x + imageBounds.width - originalBox.x;
      const maxPossibleHeight = imageBounds.y + imageBounds.height - originalBox.y;
      
      // Calculate the actual maximum based on aspect ratio
      let maxWidth, maxHeight;
      if (maxPossibleWidth / aspectRatio <= maxPossibleHeight) {
        maxWidth = maxPossibleWidth;
        maxHeight = maxPossibleWidth / aspectRatio;
      } else {
        maxHeight = maxPossibleHeight;
        maxWidth = maxPossibleHeight * aspectRatio;
      }
      
      // For left-side resizing, calculate minimum X position
      const minX = imageBounds.x;
      const maxWidthFromLeft = originalBox.x + originalBox.width - minX;
      
      // Clamp mouse position to valid range for each handle
      let clampedX = x;
      
      switch(resizeHandle) {
        case 'se':
          // Clamp X to not exceed the maximum width
          clampedX = Math.min(x, originalBox.x + maxWidth);
          newBox.width = Math.max(50, clampedX - originalBox.x);
          newBox.height = newBox.width / aspectRatio;
          break;
        case 'nw':
          // Clamp X to not go below minimum position
          clampedX = Math.max(x, originalBox.x + originalBox.width - maxWidthFromLeft);
          const nwWidth = Math.max(50, originalBox.x + originalBox.width - clampedX);
          const nwHeight = nwWidth / aspectRatio;
          newBox.width = nwWidth;
          newBox.height = nwHeight;
          newBox.x = originalBox.x + originalBox.width - nwWidth;
          newBox.y = originalBox.y + originalBox.height - nwHeight;
          break;
        case 'ne':
          // Clamp X to not exceed the maximum width
          clampedX = Math.min(x, originalBox.x + maxWidth);
          const neWidth = Math.max(50, clampedX - originalBox.x);
          const neHeight = neWidth / aspectRatio;
          newBox.width = neWidth;
          newBox.height = neHeight;
          newBox.y = originalBox.y + originalBox.height - neHeight;
          break;
        case 'sw':
          // Clamp X to not go below minimum position
          clampedX = Math.max(x, originalBox.x + originalBox.width - maxWidthFromLeft);
          const swWidth = Math.max(50, originalBox.x + originalBox.width - clampedX);
          const swHeight = swWidth / aspectRatio;
          newBox.width = swWidth;
          newBox.height = swHeight;
          newBox.x = originalBox.x + originalBox.width - swWidth;
          break;
      }
      
      const constrained = constrainCropBox(newBox);
      
      // Only update if the constrained box is valid
      if (constrained.x >= imageBounds.x && 
          constrained.y >= imageBounds.y &&
          constrained.x + constrained.width <= imageBounds.x + imageBounds.width &&
          constrained.y + constrained.height <= imageBounds.y + imageBounds.height) {
        cropBox = constrained;
        drawCanvas();
      }
    }
  }
  
  function handleMouseUp() {
    isDragging = false;
    isResizing = false;
    resizeHandle = '';
    showDimensions = false;
    hoveredHandle = '';
    drawCanvas();
  }
  
  // Touch event handlers for mobile support
  function handleTouchStart(event) {
    if (event.touches.length === 1) {
      const touch = event.touches[0];
      const rect = canvasRef.getBoundingClientRect();
      const fakeMouseEvent = {
        clientX: touch.clientX,
        clientY: touch.clientY
      };
      handleMouseDown(fakeMouseEvent);
    }
  }
  
  function handleTouchMove(event) {
    if (event.touches.length === 1) {
      event.preventDefault(); // Prevent scrolling
      const touch = event.touches[0];
      const fakeMouseEvent = {
        clientX: touch.clientX,
        clientY: touch.clientY
      };
      handleMouseMove(fakeMouseEvent);
    }
  }
  
  function handleTouchEnd(event) {
    handleMouseUp();
  }
  
  async function handleCrop() {
    if (!imageElement || !canvasRef) return;
    
    const bounds = imageBounds;
    const scale = bounds.width / imageElement.width;
    
    // Calculate crop coordinates in original image space
    const cropX = (cropBox.x - bounds.x) / scale;
    const cropY = (cropBox.y - bounds.y) / scale;
    const cropWidth = cropBox.width / scale;
    const cropHeight = cropBox.height / scale;
    
    // Create cropped canvas
    const croppedCanvas = document.createElement('canvas');
    croppedCanvas.width = cropWidth;
    croppedCanvas.height = cropHeight;
    const ctx = croppedCanvas.getContext('2d');
    
    ctx.drawImage(
      imageElement,
      cropX, cropY, cropWidth, cropHeight,
      0, 0, cropWidth, cropHeight
    );
    
    // Convert to blob
    croppedCanvas.toBlob((blob) => {
      onCrop(blob);
    }, 'image/jpeg', 0.9);
  }
  
  $effect(() => {
    if (imageLoaded) {
      drawCanvas();
    }
  });
  
  // Update canvas size on window resize
  function handleResize() {
    if (imageLoaded) {
      calculateImageBounds();
      drawCanvas();
    }
  }
  
  onMount(() => {
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  });
</script>

<div class="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
  <div class="bg-white rounded-lg max-w-4xl w-full mx-4 max-h-[90vh] flex flex-col">
    <div class="px-6 py-4 border-b">
      <h2 class="text-xl font-semibold">{title}</h2>
    </div>
    
    <div class="flex-1 p-6 overflow-hidden">
      <div 
        bind:this={containerRef}
        class="relative w-full h-[500px] bg-gray-100"
      >
        <canvas
          bind:this={canvasRef}
          width={800}
          height={500}
          class="absolute inset-0 w-full h-full"
          style="cursor: {cursorStyle}"
          onmousedown={handleMouseDown}
          onmousemove={handleMouseMove}
          onmouseup={handleMouseUp}
          onmouseleave={() => {
            if (!isDragging && !isResizing) {
              hoveredHandle = '';
              cursorStyle = 'default';
              drawCanvas();
            }
          }}
          ontouchstart={handleTouchStart}
          ontouchmove={handleTouchMove}
          ontouchend={handleTouchEnd}
        />
      </div>
      
      <div class="mt-4 text-sm text-gray-600">
        Drag to reposition • Drag corners to resize • Aspect ratio: {aspectRatio === 1 ? '1:1' : '3:1'}
      </div>
    </div>
    
    <div class="px-6 py-4 border-t flex justify-end gap-3">
      <button
        onclick={onCancel}
        class="px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
      >
        Cancel
      </button>
      <button
        onclick={handleCrop}
        class="px-4 py-2 text-white bg-blue-600 rounded-md hover:bg-blue-700"
      >
        Apply Crop
      </button>
    </div>
  </div>
</div>