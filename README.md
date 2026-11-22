# Flous Flow Employee Production Tracking

Odoo 19 Community addon for allocating actual manufactured quantities to employees on standard manufacturing orders.

The addon keeps Odoo's native stock moves, manufacturing completion, valuation and work-order timers as the source of truth. It adds employee sessions and allocations in `ff.mrp.employee.workorder.session` and `ff.mrp.employee.production.line`, validates them against `mrp.production.qty_produced`, and reports only completed manufacturing orders whose allocation exactly matches actual production. Approved allocations can be sent to a draft payslip as a standard `hr.payslip.input` using a configurable production incentive rule.

Install with:

```bash
odoo-bin -d <database> -i ff_mrp_employee_productivity --stop-after-init
```

Use the **Production Employees / موظفو الإنتاج** tab on a manufacturing order. Reports are under Manufacturing → Reporting → Employee Production. Employee statements are available from the employee smart button and the Employees list action.

## دليل الاستخدام بالعربية

1. افتح التصنيع ثم أمر التصنيع المطلوب، وبعدها تبويب **موظفو الإنتاج**.
2. أضف الموظف، تاريخ الإنتاج الفعلي، والكمية التي أنجزها. يمكن إضافة أكثر من موظف وتواريخ متعددة لنفس الأمر.
3. بعد تسجيل الكمية الفعلية في أمر التصنيع، راجع حالة التوزيع: يجب أن يساوي مجموع حصص الموظفين الكمية المنتجة. التوزيع الناقص أو الزائد لا يظهر في التقارير النهائية.
4. تقرير **إنتاج الموظفين** موجود تحت التصنيع ← التقارير، ويدعم القائمة والجدول المحوري والرسم والبحث والتجميع. يمكن استخدام تصدير القائمة القياسي إلى Excel.
5. من بطاقة الموظف استخدم زر **الإنتاج** لعرض سجلاته أو إجراء **طباعة كشف الإنتاج** لتحديد الفترة وطباعة PDF فردي. ومن قائمة الموظفين يمكن اختيار عدة موظفين لطباعة كشف موحد، صفحة مستقلة لكل موظف.
6. من أمر التشغيل استخدم **بدء العمل وجلسة الموظف**. زر البدء يستخدم مؤقت أودو القياسي، وتظهر جلسة الموظف في نفس أمر التشغيل. عند الإيقاف تُسجل الكمية التي أدخلها الموظف كتوزيع إنتاج مسودة، ويمكن مراجعتها وإرسالها للاعتماد.
7. من **مراكز العمل ← المعلومات العامة** اربط الموظفين المسموح لهم بالمركز وحدد تكلفة الساعة الافتراضية. ويمكن تحديد تكلفة خاصة بالموظف من بطاقة الموظف في حقل **تكلفة إنتاج الساعة**؛ هذه القيمة لها الأولوية على تكلفة المركز.
8. لا يمكن اعتماد التوزيع إلا بعد إكمال أمر التصنيع ووصول مجموع حصص الموظفين إلى الكمية المنتجة الفعلية. بعد الاعتماد، استخدم **إرسال إنتاج الموظفين إلى الرواتب** لإضافة قيمة الحافز إلى قسيمة راتب مسودة.

التعديل لا يستبدل تدفق أودو القياسي؛ مؤقت أمر التشغيل الأصلي يظل المرجع للوقت، والتوزيع والرواتب طبقة مراجعة إضافية. المستخدم العادي لا يستطيع تعديل توزيع أمر مكتمل أو معتمد، بينما مدير التصنيع يستطيع تصحيح السجل وتُسجل عملية التصحيح في chatter. الأوامر الملغاة لا تقبل تعديل التوزيع. عناصر Shop Floor Enterprise مثل لوحات الباركود وتعليمات التشغيل التفاعلية ليست جزءًا من هذا الموديول؛ الموديول يستخدم شاشة أوامر التشغيل القياسية مع جلسات الموظفين.
