export async function getRecaptchaToken(action: string): Promise<string> {
    return new Promise((resolve, reject) => {
      if (!window.grecaptcha || !window.grecaptcha.ready) {
        return reject(new Error("reCAPTCHA not loaded or wrong script"));
      }
      window.grecaptcha.ready(() => {
        window.grecaptcha
          .execute(process.env.NEXT_PUBLIC_SITE_KEY!, { action })
          .then(resolve)
          .catch(reject);
      });
    });
  }  

