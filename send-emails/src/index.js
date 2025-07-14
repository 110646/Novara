export default {
  async fetch(request, env) {
    console.log("🔐 Using Postmark API token:", env.POSTMARK_API_TOKEN ? "✅ Loaded" : "❌ Not Found");

    try {
      const { template, student, professors } = await request.json();
      console.log(`📨 Sending ${professors.length} emails`);

      for (const prof of professors) {
        const personalized = template
          .replace(/{{\s*professor_name\s*}}|{\s*professor_name\s*}/g, prof.last_name)
          .replace(/{{\s*university\s*}}|{\s*university\s*}/g, prof.university)
          .replace(/{{\s*major\s*}}|{\s*major\s*}/g, student.major)
          .replace(/{{\s*student_name\s*}}|{\s*student_name\s*}/g, student.name);

        const payload = {
          From: `${student.name} <research@connectnovara.com>`,
          To: prof.email,
          Subject: `Research Opportunity – Inquiry from ${student.name}`,
          TextBody: personalized,
          HtmlBody: personalized.replace(/\n/g, "<br>"),
          ReplyTo: student.email,
          TrackOpens: true,
          Metadata: {
            user_id: String(student.id),
            professor_id: prof.id
          }
        };

        console.log("📦 Postmark Payload:", JSON.stringify(payload, null, 2));

        const res = await fetch("https://api.postmarkapp.com/email", {
          method: "POST",
          headers: {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Postmark-Server-Token": env.POSTMARK_API_TOKEN
          },
          body: JSON.stringify(payload)
        });

        console.log(`✅ Postmark response: ${res.status}`);
        if (res.status >= 400) {
          const error = await res.text();
          console.error("❌ Postmark error:", error);
        }

        // ✅ Log the sent email to your Django backend
        const logRes = await fetch("https://8f6a48d46a7d.ngrok-free.app/log-sent-email/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            user_id: student.id,
            professor_email: prof.email,
            university: prof.university,
            email_body: personalized,
            smtp_id: null  // You can update this if Postmark returns a message ID
          })
        });

        console.log(`📤 Django log response: ${logRes.status}`);
        if (logRes.status >= 400) {
          const logError = await logRes.text();
          console.error("❌ Django log error:", logError);
        }
      }

      return new Response("Emails sent and logged successfully");
    } catch (err) {
      console.error("❌ Worker error:", err);
      return new Response(`Error: ${err.message}`);
    }
  }
};
