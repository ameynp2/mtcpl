from hrms.hr.doctype.shift_type.shift_type import ShiftType

from mtcpl.overrides.leave_application import get_approved_short_leave


class CustomShiftType(ShiftType):
	def get_attendance(self, logs):
		"""Count approved Short Leave hours as worked time before the Absent / Half Day / Present
		thresholds are applied. The recorded working hours stay the actual hours from check-ins."""
		status, working_hours, late_entry, early_exit, in_time, out_time = super().get_attendance(logs)

		_short_leave, hours = get_approved_short_leave(logs[0].employee, logs[0].shift_start.date())
		if hours:
			credited_hours = working_hours + hours
			if (
				self.working_hours_threshold_for_absent
				and credited_hours < self.working_hours_threshold_for_absent
			):
				status = "Absent"
			elif (
				self.working_hours_threshold_for_half_day
				and credited_hours < self.working_hours_threshold_for_half_day
			):
				status = "Half Day"
			else:
				status = "Present"

		return status, working_hours, late_entry, early_exit, in_time, out_time
