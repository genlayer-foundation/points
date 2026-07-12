(function() {
    'use strict';
    
    document.addEventListener('DOMContentLoaded', function() {
        const contributionTypeSelect = document.getElementById('id_contribution_type');
        const infoContainer = document.querySelector('.field-contribution_type_info .readonly');
        
        if (!contributionTypeSelect || !infoContainer) {
            return;
        }
        
        // Function to update contribution type info
        function updateContributionTypeInfo() {
            const selectedValue = contributionTypeSelect.value;
            
            if (!selectedValue) {
                infoContainer.textContent = '-';
                return;
            }
            
            // Get the admin URL prefix
            const pathParts = window.location.pathname.split('/');
            const adminIndex = pathParts.indexOf('admin');
            const adminPrefix = pathParts.slice(0, adminIndex + 1).join('/');
            
            // Fetch contribution type info
            fetch(`${adminPrefix}/contributions/contribution/contribution-type-info/${selectedValue}/`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        infoContainer.textContent = '-';
                    } else {
                        const info = document.createElement('div');
                        info.id = 'contribution-type-info';
                        info.style.padding = '10px';
                        info.style.background = '#f8f9fa';
                        info.style.borderRadius = '4px';
                        info.style.margin = '5px 0';

                        function appendLine(label, value) {
                            const strong = document.createElement('strong');
                            strong.textContent = label;
                            info.appendChild(strong);
                            info.appendChild(document.createTextNode(` ${value}`));
                            info.appendChild(document.createElement('br'));
                        }

                        appendLine('Points Range:', `${data.min_points}-${data.max_points} points`);
                        appendLine('Current Multiplier:', `${data.current_multiplier}x`);
                        if (data.description) {
                            const strong = document.createElement('strong');
                            strong.textContent = 'Description:';
                            info.appendChild(strong);
                            info.appendChild(document.createTextNode(` ${data.description}`));
                        }
                        infoContainer.replaceChildren(info);
                    }
                })
                .catch(error => {
                    console.error('Error fetching contribution type info:', error);
                    const errorMessage = document.createElement('em');
                    errorMessage.textContent = 'Error loading info';
                    infoContainer.replaceChildren(errorMessage);
                });
        }
        
        // Add event listener for changes
        contributionTypeSelect.addEventListener('change', updateContributionTypeInfo);
        
        // Also update points field placeholder based on range
        contributionTypeSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            const pointsField = document.getElementById('id_points');
            
            if (pointsField && selectedOption.value) {
                // We'll need to fetch the info to get min/max points
                fetch(`${window.location.pathname.split('/').slice(0, -3).join('/')}/contribution-type-info/${selectedOption.value}/`)
                    .then(response => response.json())
                    .then(data => {
                        if (!data.error) {
                            pointsField.setAttribute('min', data.min_points);
                            pointsField.setAttribute('max', data.max_points);
                            pointsField.setAttribute('placeholder', `${data.min_points}-${data.max_points} points`);
                        }
                    })
                    .catch(error => console.error('Error updating points field:', error));
            }
        });
    });
})();
