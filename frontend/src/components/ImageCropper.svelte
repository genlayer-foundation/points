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
  
  onMount(() => {
    loadImage();
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
  
  function initializeCropBox() {
    if (!imageElement || !containerRef) return;
    
    const containerRect = containerRef.getBoundingClientRect();
    const scale = Math.min(
      containerRect.width / imageElement.width,
      containerRect.height / imageElement.height
    );
    
    const displayWidth = imageElement.width * scale;
    const displayHeight = imageElement.height * scale;
    
    // Initialize crop box to center with 80% of image size
    const cropSize = Math.min(displayWidth, displayHeight) * 0.8;
    const cropWidth = cropSize;
    const cropHeight = cropSize / aspectRatio;
    
    cropBox = {
      x: (containerRect.width - cropWidth) / 2,
      y: (containerRect.height - cropHeight) / 2,
      width: cropWidth,
      height: cropHeight
    };
  }
  
  function drawCanvas() {
    if (!canvasRef || !imageElement || !imageLoaded) return;
    
    const ctx = canvasRef.getContext('2d');
    const containerRect = containerRef.getBoundingClientRect();
    
    // Clear canvas
    ctx.clearRect(0, 0, canvasRef.width, canvasRef.height);
    
    // Calculate scale to fit image in container
    const scale = Math.min(
      containerRect.width / imageElement.width,
      containerRect.height / imageElement.height
    );
    
    const displayWidth = imageElement.width * scale;
    const displayHeight = imageElement.height * scale;
    const offsetX = (containerRect.width - displayWidth) / 2;
    const offsetY = (containerRect.height - displayHeight) / 2;
    
    // Draw image
    ctx.drawImage(imageElement, offsetX, offsetY, displayWidth, displayHeight);
    
    // Draw dark overlay
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    ctx.fillRect(0, 0, canvasRef.width, canvasRef.height);
    
    // Clear crop area (show original image)
    ctx.save();
    ctx.globalCompositeOperation = 'destination-out';
    ctx.fillRect(cropBox.x, cropBox.y, cropBox.width, cropBox.height);
    ctx.restore();
    
    // Draw crop box border
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2;
    ctx.strokeRect(cropBox.x, cropBox.y, cropBox.width, cropBox.height);
    
    // Draw resize handles
    const handleSize = 8;
    ctx.fillStyle = '#fff';
    
    // Corners
    ctx.fillRect(cropBox.x - handleSize/2, cropBox.y - handleSize/2, handleSize, handleSize);
    ctx.fillRect(cropBox.x + cropBox.width - handleSize/2, cropBox.y - handleSize/2, handleSize, handleSize);
    ctx.fillRect(cropBox.x - handleSize/2, cropBox.y + cropBox.height - handleSize/2, handleSize, handleSize);
    ctx.fillRect(cropBox.x + cropBox.width - handleSize/2, cropBox.y + cropBox.height - handleSize/2, handleSize, handleSize);
  }
  
  function handleMouseDown(event) {
    const rect = canvasRef.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    // Check if clicking on resize handles
    const handleSize = 16;
    
    if (Math.abs(x - cropBox.x) < handleSize && Math.abs(y - cropBox.y) < handleSize) {
      isResizing = true;
      resizeHandle = 'nw';
    } else if (Math.abs(x - (cropBox.x + cropBox.width)) < handleSize && Math.abs(y - cropBox.y) < handleSize) {
      isResizing = true;
      resizeHandle = 'ne';
    } else if (Math.abs(x - cropBox.x) < handleSize && Math.abs(y - (cropBox.y + cropBox.height)) < handleSize) {
      isResizing = true;
      resizeHandle = 'sw';
    } else if (Math.abs(x - (cropBox.x + cropBox.width)) < handleSize && Math.abs(y - (cropBox.y + cropBox.height)) < handleSize) {
      isResizing = true;
      resizeHandle = 'se';
    } else if (x >= cropBox.x && x <= cropBox.x + cropBox.width && y >= cropBox.y && y <= cropBox.y + cropBox.height) {
      isDragging = true;
      dragStart = { x: x - cropBox.x, y: y - cropBox.y };
    }
  }
  
  function handleMouseMove(event) {
    if (!isDragging && !isResizing) return;
    
    const rect = canvasRef.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    if (isDragging) {
      cropBox.x = Math.max(0, Math.min(rect.width - cropBox.width, x - dragStart.x));
      cropBox.y = Math.max(0, Math.min(rect.height - cropBox.height, y - dragStart.y));
    } else if (isResizing) {
      let newBox = { ...cropBox };
      
      switch(resizeHandle) {
        case 'se':
          newBox.width = Math.max(50, x - cropBox.x);
          newBox.height = newBox.width / aspectRatio;
          break;
        case 'nw':
          const sizeDiff = cropBox.x - x;
          newBox.width = Math.max(50, cropBox.width + sizeDiff);
          newBox.height = newBox.width / aspectRatio;
          newBox.x = cropBox.x + cropBox.width - newBox.width;
          newBox.y = cropBox.y + cropBox.height - newBox.height;
          break;
        case 'ne':
          newBox.width = Math.max(50, x - cropBox.x);
          newBox.height = newBox.width / aspectRatio;
          newBox.y = cropBox.y + cropBox.height - newBox.height;
          break;
        case 'sw':
          const swSizeDiff = cropBox.x - x;
          newBox.width = Math.max(50, cropBox.width + swSizeDiff);
          newBox.height = newBox.width / aspectRatio;
          newBox.x = cropBox.x + cropBox.width - newBox.width;
          break;
      }
      
      // Keep within bounds
      if (newBox.x >= 0 && newBox.y >= 0 && 
          newBox.x + newBox.width <= rect.width && 
          newBox.y + newBox.height <= rect.height) {
        cropBox = newBox;
      }
    }
    
    drawCanvas();
  }
  
  function handleMouseUp() {
    isDragging = false;
    isResizing = false;
    resizeHandle = '';
  }
  
  async function handleCrop() {
    if (!imageElement || !canvasRef) return;
    
    const containerRect = containerRef.getBoundingClientRect();
    const scale = Math.min(
      containerRect.width / imageElement.width,
      containerRect.height / imageElement.height
    );
    
    const displayWidth = imageElement.width * scale;
    const displayHeight = imageElement.height * scale;
    const offsetX = (containerRect.width - displayWidth) / 2;
    const offsetY = (containerRect.height - displayHeight) / 2;
    
    // Calculate crop coordinates in original image space
    const cropX = (cropBox.x - offsetX) / scale;
    const cropY = (cropBox.y - offsetY) / scale;
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
          class="absolute inset-0 w-full h-full cursor-move"
          onmousedown={handleMouseDown}
          onmousemove={handleMouseMove}
          onmouseup={handleMouseUp}
          onmouseleave={handleMouseUp}
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