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

        console.log(`📤 Sending to: ${prof.email}`);
        console.log(`📬 Subject: Research Opportunity – Inquiry from ${student.name}`);
        console.log(`📝 Email body:\n${personalized}`);

        const sendgridRes = await fetch("https://api.sendgrid.com/v3/mail/send", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${env.SENDGRID_API_KEY}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            personalizations: [{
              to: [{ email: prof.email }],
              subject: `Research Opportunity – Inquiry from ${student.name}`,
              custom_args: {
                user_id: student.id,
                student_email: student.email
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
            }]
          })
        });

        console.log(`✅ SendGrid response: ${sendgridRes.status}`);

        if (sendgridRes.status >= 400) {
          const errorBody = await sendgridRes.text();
          console.log(`❌ SendGrid error response:\n${errorBody}`);
        }
      }

      return new Response("Emails sent");
    } catch (err) {
      console.log("❌ Worker error:", err);
      return new Response(`Error: ${err.message}`);
    }
  }
};
