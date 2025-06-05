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
                infoContainer.innerHTML = '-';
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
                        infoContainer.innerHTML = '-';
                    } else {
                        let html = '<div id="contribution-type-info" style="padding: 10px; background: #f8f9fa; border-radius: 4px; margin: 5px 0;">';
                        html += `<strong>Points Range:</strong> ${data.min_points}-${data.max_points} points<br>`;
                        html += `<strong>Current Multiplier:</strong> ${data.current_multiplier}x<br>`;
                        if (data.description) {
                            html += `<strong>Description:</strong> ${data.description}`;
                        }
                        html += '</div>';
                        infoContainer.innerHTML = html;
                    }
                })
                .catch(error => {
                    console.error('Error fetching contribution type info:', error);
                    infoContainer.innerHTML = '<em>Error loading info</em>';
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