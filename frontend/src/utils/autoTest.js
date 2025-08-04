// Auto-test script for MCP Sampling workflow
// Run in browser console: autoTest()

window.autoTest = async function() {
  console.log('🚀 Starting automated MCP Sampling test...');
  
  // Step 1: Fill prediction input
  const input = document.querySelector('textarea[placeholder*="Enter your call"]');
  if (!input) {
    console.error('❌ Could not find prediction input');
    return;
  }
  
  input.value = 'it will rain';
  input.dispatchEvent(new Event('input', { bubbles: true }));
  console.log('✅ Step 1: Entered prediction "it will rain"');
  
  // Step 2: Submit form
  await new Promise(resolve => setTimeout(resolve, 100)); // Wait for input to register
  
  const form = document.querySelector('form');
  const submitBtn = document.querySelector('button[type="submit"]');
  
  if (!submitBtn) {
    console.error('❌ Could not find submit button');
    return;
  }
  
  // Trigger form submission
  if (form) {
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  } else {
    submitBtn.click();
  }
  console.log('✅ Step 2: Submitted prediction');
  
  // Step 3: Wait for reviewable sections to appear
  console.log('⏳ Step 3: Waiting for review to complete...');
  
  const waitForReviewableSections = () => {
    return new Promise((resolve) => {
      const checkForSections = () => {
        // Look for sections with dashed borders (reviewable sections)
        const reviewableSections = document.querySelectorAll('[style*="dashed"], .reviewable-section');
        if (reviewableSections.length > 0) {
          console.log(`✅ Step 3: Found ${reviewableSections.length} reviewable sections`);
          resolve(reviewableSections);
        } else {
          setTimeout(checkForSections, 500);
        }
      };
      checkForSections();
    });
  };
  
  const sections = await waitForReviewableSections();
  
  // Step 4: Click prediction_statement section
  const predictionSection = Array.from(sections).find(section => 
    section.textContent.includes('it will rain')
  );
  
  if (!predictionSection) {
    console.error('❌ Could not find prediction statement section');
    return;
  }
  
  predictionSection.click();
  console.log('✅ Step 4: Clicked prediction statement section');
  
  // Step 5: Wait for modal and fill answers
  const waitForModal = () => {
    return new Promise((resolve) => {
      const checkForModal = () => {
        const modal = document.querySelector('[role="dialog"], .modal, .improvement-modal');
        if (modal && modal.style.display !== 'none') {
          console.log('✅ Step 5: Modal appeared');
          resolve(modal);
        } else {
          setTimeout(checkForModal, 200);
        }
      };
      checkForModal();
    });
  };
  
  await waitForModal();
  
  // Step 6: Fill in the answers
  const answers = ['New York City', 'tomorrow', 'measurable'];
  const inputs = document.querySelectorAll('input[type="text"], textarea');
  
  let answerIndex = 0;
  for (const input of inputs) {
    if (input.closest('.modal, [role="dialog"]') && answerIndex < answers.length) {
      input.value = answers[answerIndex];
      input.dispatchEvent(new Event('input', { bubbles: true }));
      console.log(`✅ Step 6.${answerIndex + 1}: Filled answer "${answers[answerIndex]}"`);
      answerIndex++;
    }
  }
  
  // Step 7: Submit answers
  const submitAnswersBtn = document.querySelector('.modal button[type="submit"], [role="dialog"] button[type="submit"]');
  if (!submitAnswersBtn) {
    console.error('❌ Could not find submit answers button');
    return;
  }
  
  submitAnswersBtn.click();
  console.log('✅ Step 7: Submitted answers');
  
  // Step 8: Wait for improvement to complete
  console.log('⏳ Step 8: Waiting for improvement to complete...');
  
  const waitForImprovement = () => {
    return new Promise((resolve) => {
      const checkForImprovement = () => {
        const callDetails = document.querySelector('.structured-response, .call-details');
        if (callDetails && callDetails.textContent.includes('New York City')) {
          console.log('✅ Step 8: Improvement completed - found "New York City" in response');
          resolve();
        } else {
          setTimeout(checkForImprovement, 500);
        }
      };
      checkForImprovement();
    });
  };
  
  await waitForImprovement();
  
  console.log('🎉 Automated test completed successfully!');
  console.log('📊 Test Results:');
  console.log('- Initial prediction: "it will rain"');
  console.log('- Clarifications: New York City, tomorrow, measurable');
  console.log('- Final result should show improved prediction with location and timeframe');
};

console.log('🔧 Auto-test loaded! Run autoTest() to start the test.');