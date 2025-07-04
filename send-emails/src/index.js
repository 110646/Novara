export default {
  async fetch(request, env) {
    console.log("🔐 Using SendGrid API key:", env.SENDGRID_API_KEY ? "✅ Loaded" : "❌ Not Found");

    try {
      const { template, student, professors } = await request.json();
      console.log(`📨 Sending ${professors.length} emails`);

      for (const prof of professors) {
        const personalized = template
          .replace(/{{\s*professor_name\s*}}|{\s*professor_name\s*}/g, prof.last_name)
          .replace(/{{\s*university\s*}}|{\s*university\s*}/g, prof.university)
          .replace(/{{\s*major\s*}}|{\s*major\s*}/g, student.major)
          .replace(/{{\s*student_name\s*}}|{\s*student_name\s*}/g, student.name);

        const body = {
          personalizations: [{
            to: [{ email: prof.email }],
            subject: `Research Opportunity – Inquiry from ${student.name}`,
            custom_args: {
              user_id: String(student.id),
              professor_id: prof.id
            }
          }],
          from: {
            email: "research@connectnovara.com",
            name: student.name
          },
          reply_to: {
            email: student.email,
            name: student.name
          },
          content: [{
            type: "text/plain",
            value: personalized
          }],
          tracking_settings: {
            open_tracking: {
              enable: true
            }
          },
          mail_settings: {
            event_payload_version: 2  // ✅ required for SendGrid to include custom_args in webhooks
          }
        };

        console.log("📦 SendGrid Payload:", JSON.stringify(body, null, 2));

        const sendgridRes = await fetch("https://api.sendgrid.com/v3/mail/send", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${env.SENDGRID_API_KEY}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify(body)
        });

        console.log(`✅ SendGrid response: ${sendgridRes.status}`);

        if (sendgridRes.status >= 400) {
          const errorText = await sendgridRes.text();
          console.log(`❌ SendGrid error:\n${errorText}`);
        }
      }

      return new Response("Emails sent");
    } catch (err) {
      console.log("❌ Worker error:", err);
      return new Response(`Error: ${err.message}`);
    }
  }
};
